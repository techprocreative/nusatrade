"""AI Supervisor API with LLM integration."""

import asyncio
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.config import get_settings
from app.core.logging import get_logger
from app.models.llm import LLMConversation as Conversation, LLMMessage as Message


router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context_type: str = "general"  # general, trade_analysis, market_summary


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    tokens_used: int = 0


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    message_count: int


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime


# LLM Client wrapper
class LLMClient:
    """Unified LLM client supporting OpenAI-compatible APIs with database config support."""

    def __init__(self):
        self.client = None
        self.anthropic_client = None  # Fallback only
        self._db_config_loaded = False  # Track if config was loaded from database
        self._current_model = None
        self._init_clients()

    def _init_clients(self, db: Optional[Session] = None):
        """Initialize LLM client with OpenAI-compatible interface.
        
        Args:
            db: Optional database session to load config from database.
                If provided, loads from SettingsService with env fallback.
                If None, uses environment variables only.
        """
        # Load config from database if db session provided
        if db:
            try:
                from app.core.settings_service import SettingsService
                service = SettingsService(db)
                config = service.get_llm_config(
                    fallback_api_key=settings.llm_api_key or settings.openai_api_key,
                    fallback_base_url=settings.llm_base_url,
                    fallback_model=settings.llm_model or settings.openai_model
                )
            except Exception as e:
                logger.warning(f"Failed to load config from database, using env vars: {e}")
                config = settings.effective_llm_config
        else:
            # Use environment variables
            config = settings.effective_llm_config
        
        if config["api_key"]:
            try:
                import openai
                # Support custom base_url for OpenAI-compatible providers
                # If base_url is None, OpenAI SDK uses default (https://api.openai.com/v1)
                self.client = openai.OpenAI(
                    api_key=config["api_key"],
                    base_url=config["base_url"]
                )
                self._current_model = config["model"]
                self._db_config_loaded = db is not None
                provider = config["base_url"] or "OpenAI"
                logger.info(f"LLM client initialized (provider: {provider}, model: {config['model']}, from_db: {self._db_config_loaded})")
            except ImportError:
                logger.warning("openai package not installed")
        else:
            logger.warning(f"No LLM API key found (from_db: {db is not None})")

        # Keep Anthropic as fallback
        if settings.anthropic_api_key:
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                logger.info("Anthropic fallback client initialized")
            except ImportError:
                logger.warning("anthropic package not installed")
    
    def reload_config(self, db: Session):
        """Reload LLM configuration from database.
        
        This allows runtime configuration changes without restarting the server.
        
        Args:
            db: Database session to load config from
        """
        logger.info("Reloading LLM configuration from database")
        self._init_clients(db)

    async def chat(
        self,
        messages: List[dict],
        system_prompt: str = "",
    ) -> tuple[str, int]:
        """Send chat request to LLM and get response."""
        
        # Try unified OpenAI-compatible client first
        if self.client:
            try:
                full_messages = []
                if system_prompt:
                    full_messages.append({"role": "system", "content": system_prompt})
                full_messages.extend(messages)

                response = self.client.chat.completions.create(
                    model=self._current_model or settings.effective_llm_config["model"],
                    messages=full_messages,
                    max_tokens=1000,
                    temperature=0.7,
                )
                content = response.choices[0].message.content
                tokens = response.usage.total_tokens if response.usage else 0
                return content, tokens
            except Exception as e:
                logger.error(f"LLM API error: {e}")
                # Fall through to Anthropic fallback

        # Fallback to Anthropic
        if self.anthropic_client:
            try:
                response = self.anthropic_client.messages.create(
                    model=settings.anthropic_model,
                    max_tokens=1000,
                    system=system_prompt,
                    messages=messages,
                )
                content = response.content[0].text
                tokens = response.usage.input_tokens + response.usage.output_tokens
                return content, tokens
            except Exception as e:
                logger.error(f"Anthropic error: {e}")

        # No LLM available - return helpful message
        return self._fallback_response(messages[-1]["content"] if messages else ""), 0

    def _fallback_response(self, query: str) -> str:
        """Provide fallback response when no LLM is available."""
        return (
            "AI Supervisor is not fully configured. To enable AI features, "
            "please add OPENAI_API_KEY or ANTHROPIC_API_KEY to your environment. "
            f"\n\nYour query was: {query[:100]}..."
        )


# Global LLM client
llm_client = LLMClient()


# System prompts
SYSTEM_PROMPTS = {
    "general": """You are an expert forex trading assistant. You help traders with:
- Analyzing market conditions
- Explaining trading concepts
- Reviewing trading performance
- Providing educational content

Be concise, practical, and always consider risk management.""",

    "trade_analysis": """You are analyzing a forex trade. Consider:
- Entry and exit points
- Risk/reward ratio
- Market conditions at the time
- What could be improved

Provide constructive feedback.""",

    "market_summary": """Provide a concise market summary for forex traders. Include:
- Key price levels
- Major trends
- Upcoming events that could impact the market
- Overall market sentiment""",
}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Chat with the AI Supervisor."""
    
    # Ensure LLM client is initialized with database config
    if not llm_client._db_config_loaded:
        llm_client.reload_config(db)
    
    # Get or create conversation
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id,
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(
            id=str(uuid4()),
            user_id=current_user.id,
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
        )
        db.add(conversation)
        db.commit()

    # Get conversation history
    history = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at).limit(20).all()

    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": request.message})

    # Get response from LLM
    system_prompt = SYSTEM_PROMPTS.get(request.context_type, SYSTEM_PROMPTS["general"])
    reply, tokens = await llm_client.chat(messages, system_prompt)

    # Save messages
    user_msg = Message(
        id=str(uuid4()),
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    assistant_msg = Message(
        id=str(uuid4()),
        conversation_id=conversation.id,
        role="assistant",
        content=reply,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

    return ChatResponse(
        reply=reply,
        conversation_id=str(conversation.id),
        tokens_used=tokens,
    )


@router.get("/conversations", response_model=List[ConversationOut])
def list_conversations(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
    limit: int = 20,
):
    """List user's conversations."""
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.created_at.desc()).limit(limit).all()

    return [
        ConversationOut(
            id=str(c.id),
            title=c.title or "Untitled",
            created_at=c.created_at,
            message_count=db.query(Message).filter(Message.conversation_id == c.id).count(),
        )
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=List[MessageOut])
def get_conversation(
    conversation_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get messages in a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    return [
        MessageOut(
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Delete a conversation."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.delete(conversation)
    db.commit()

    return {"deleted": conversation_id}


@router.get("/analysis/daily")
async def daily_analysis(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get daily market analysis."""
    # Ensure LLM client is initialized with database config
    if not llm_client._db_config_loaded:
        llm_client.reload_config(db)
    
    prompt = """Provide a brief daily forex market analysis covering:
1. Major pairs outlook (EURUSD, GBPUSD, USDJPY)
2. Key support and resistance levels
3. Economic events to watch today
4. Overall market sentiment

Keep it concise and actionable."""

    reply, _ = await llm_client.chat(
        [{"role": "user", "content": prompt}],
        SYSTEM_PROMPTS["market_summary"],
    )

    return {
        "summary": reply,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/analysis/{symbol}")
async def symbol_analysis(
    symbol: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get analysis for a specific symbol."""
    # Ensure LLM client is initialized with database config
    if not llm_client._db_config_loaded:
        llm_client.reload_config(db)
    
    prompt = f"""Analyze {symbol.upper()} forex pair:
1. Current trend direction
2. Key support and resistance levels
3. Technical indicators summary (RSI, MACD, Moving Averages)
4. Recommended trading bias

Keep the analysis practical and concise."""

    reply, _ = await llm_client.chat(
        [{"role": "user", "content": prompt}],
        SYSTEM_PROMPTS["general"],
    )

    return {
        "symbol": symbol.upper(),
        "analysis": reply,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/recommendations")
async def get_recommendations(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get trading recommendations based on user's actual trading history."""
    from app.models.trade import Trade
    
    # Ensure LLM client is initialized with database config
    if not llm_client._db_config_loaded:
        llm_client.reload_config(db)
    
    # Fetch user's trade history for personalized analysis
    trades = db.query(Trade).filter(
        Trade.user_id == current_user.id,
        Trade.close_time.isnot(None)  # Only closed trades
    ).order_by(Trade.close_time.desc()).limit(50).all()
    
    # Initialize trading analysis variables
    trading_style = "new_trader"
    avg_trade_duration_hours = 0
    session_preferences = {"asian": 0, "london": 0, "new_york": 0}
    win_rate = 0
    total_profit = 0
    
    # Calculate trading statistics
    if trades:
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.profit and float(t.profit) > 0]
        losing_trades = [t for t in trades if t.profit and float(t.profit) < 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        total_profit = sum(float(t.profit or 0) for t in trades)
        
        avg_win = (sum(float(t.profit) for t in winning_trades) / len(winning_trades)) if winning_trades else 0
        avg_loss = (sum(float(t.profit) for t in losing_trades) / len(losing_trades)) if losing_trades else 0
        
        # Get most traded symbols
        symbol_counts = {}
        for t in trades:
            symbol_counts[t.symbol] = symbol_counts.get(t.symbol, 0) + 1
        top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Get trade direction preference
        buy_trades = [t for t in trades if t.trade_type == "BUY"]
        sell_trades = [t for t in trades if t.trade_type == "SELL"]
        
        # === NEW: Calculate trade duration and trading style ===
        trade_durations = []
        for t in trades:
            if t.open_time and t.close_time:
                duration = (t.close_time - t.open_time).total_seconds() / 3600  # hours
                trade_durations.append(duration)
        
        if trade_durations:
            avg_trade_duration_hours = sum(trade_durations) / len(trade_durations)
            
            # Classify trading style based on average trade duration
            if avg_trade_duration_hours < 1:
                trading_style = "scalper"
            elif avg_trade_duration_hours < 24:
                trading_style = "day_trader"
            else:
                trading_style = "swing_trader"
        
        # === NEW: Calculate session preferences ===
        for t in trades:
            if t.open_time:
                hour = t.open_time.hour
                # Asian session: 00:00-08:00 UTC
                if 0 <= hour < 8:
                    session_preferences["asian"] += 1
                # London session: 08:00-16:00 UTC
                elif 8 <= hour < 16:
                    session_preferences["london"] += 1
                # New York session: 13:00-21:00 UTC (overlap with London)
                elif 13 <= hour < 21:
                    session_preferences["new_york"] += 1
        
        trade_history_context = f"""
USER'S TRADING HISTORY (Last {total_trades} closed trades):
- Win Rate: {win_rate:.1f}%
- Total P/L: ${total_profit:.2f}
- Average Win: ${avg_win:.2f}
- Average Loss: ${avg_loss:.2f}
- Risk:Reward Ratio: {abs(avg_win/avg_loss):.2f}:1 (based on averages)
- Most Traded: {', '.join([f'{s[0]} ({s[1]} trades)' for s in top_symbols])}
- Direction Preference: {len(buy_trades)} BUY / {len(sell_trades)} SELL trades
- Trading Style: {trading_style} (avg duration: {avg_trade_duration_hours:.1f} hours)
- Session Preferences: Asian: {session_preferences['asian']}, London: {session_preferences['london']}, NY: {session_preferences['new_york']}
"""
    else:
        trade_history_context = """
USER'S TRADING HISTORY:
- No closed trades yet (new trader)
"""
    
    prompt = f"""{trade_history_context}

Based on this trading history, provide 3-5 specific, actionable recommendations to improve trading performance. Focus on:
1. Risk management adjustments based on actual win rate
2. Position sizing optimization
3. Entry/exit timing improvements
4. Symbol selection guidance
5. Emotional discipline tips

Be specific and reference the actual statistics above where relevant."""

    reply, _ = await llm_client.chat(
        [{"role": "user", "content": prompt}],
        SYSTEM_PROMPTS["general"],
    )

    return {
        "recommendations": reply,
        "trade_stats": {
            "total_trades": len(trades) if trades else 0,
            "win_rate": win_rate if trades else 0,
            "total_pnl": total_profit if trades else 0,
        },
        "trading_style": trading_style,
        "avg_trade_duration_hours": round(avg_trade_duration_hours, 1),
        "session_preferences": session_preferences,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


# ==================== AI STRATEGY GENERATION ====================

class AIStrategyRequest(BaseModel):
    prompt: str
    symbol: Optional[str] = "EURUSD"
    timeframe: Optional[str] = "H1"
    risk_profile: Optional[str] = "moderate"  # conservative, moderate, aggressive
    preferred_indicators: Optional[List[str]] = None


class StrategyParameter(BaseModel):
    name: str
    type: str = "number"
    default_value: str | int | float | bool
    description: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None


class StrategyRule(BaseModel):
    id: str
    condition: str
    action: str
    description: str


class TrailingStopConfig(BaseModel):
    """Trailing stop configuration for strategies."""
    enabled: bool = False
    trailing_type: str = "atr_based"  # fixed_pips, atr_based, percentage
    activation_pips: float = 20.0
    trail_distance_pips: float = 15.0
    atr_multiplier: float = 1.5
    breakeven_enabled: bool = True
    breakeven_pips: float = 15.0


class RiskManagement(BaseModel):
    """Risk management configuration for strategies."""
    # Stop Loss
    stop_loss_type: str = "atr_based"
    stop_loss_value: float = 2.0
    
    # Take Profit
    take_profit_type: str = "risk_reward"
    take_profit_value: float = 2.0
    
    # Trailing Stop
    trailing_stop: Optional[TrailingStopConfig] = None
    
    # Position Sizing
    max_position_size: float = 0.1
    risk_per_trade_percent: float = 2.0
    max_daily_loss: Optional[float] = None


class GeneratedStrategy(BaseModel):
    id: str
    name: str
    description: str
    strategy_type: str = "ai_generated"
    code: str
    parameters: List[StrategyParameter]
    indicators: List[str]
    entry_rules: List[StrategyRule]
    exit_rules: List[StrategyRule]
    risk_management: RiskManagement


class AIStrategyResponse(BaseModel):
    strategy: GeneratedStrategy
    explanation: str
    warnings: List[str]
    suggested_improvements: List[str]


STRATEGY_SYSTEM_PROMPT = """You are an expert algorithmic trading strategy designer. 
When given a strategy description, you must generate a complete trading strategy in JSON format.

The response MUST be valid JSON with the following structure:
{
    "name": "Strategy Name",
    "description": "Brief description",
    "code": "# Python-like pseudocode for the strategy logic",
    "parameters": [
        {"name": "param_name", "type": "number", "default_value": 14, "description": "Description", "min": 1, "max": 100}
    ],
    "indicators": ["RSI", "EMA"],
    "entry_rules": [
        {"id": "entry_1", "condition": "RSI < 30 AND price > EMA(20)", "action": "BUY", "description": "Buy on oversold"}
    ],
    "exit_rules": [
        {"id": "exit_1", "condition": "RSI > 70 OR hit_stop_loss OR hit_take_profit", "action": "CLOSE", "description": "Exit on overbought"}
    ],
    "risk_management": {
        "stop_loss_type": "atr_based",
        "stop_loss_value": 2.0,
        "take_profit_type": "risk_reward",
        "take_profit_value": 2.0,
        "trailing_stop": {
            "enabled": true,
            "trailing_type": "atr_based",
            "activation_pips": 20,
            "trail_distance_pips": 15,
            "atr_multiplier": 1.5,
            "breakeven_enabled": true,
            "breakeven_pips": 15
        },
        "max_position_size": 0.1,
        "risk_per_trade_percent": 2.0,
        "max_daily_loss": 200
    },
    "explanation": "Detailed explanation of the strategy logic",
    "warnings": ["List of potential risks or limitations"],
    "suggested_improvements": ["List of ways to improve the strategy"]
}

Risk management field descriptions:
- stop_loss_type: "fixed_pips", "atr_based", or "percentage"
- stop_loss_value: For atr_based, this is the ATR multiplier (e.g., 2.0 means 2x ATR)
- take_profit_type: "fixed_pips", "risk_reward", or "atr_based"
- take_profit_value: For risk_reward, this is the R:R ratio (e.g., 2.0 means 2:1 reward:risk)
- trailing_stop.enabled: Whether to use trailing stop
- trailing_stop.trailing_type: "fixed_pips", "atr_based", or "percentage"
- trailing_stop.activation_pips: Pips of profit before trailing starts
- trailing_stop.breakeven_enabled: Move SL to breakeven after breakeven_pips profit

Consider the risk profile:
- conservative: ATR-based SL (2.5x), R:R 1.5:1, trailing enabled, lower position sizes (0.05)
- moderate: ATR-based SL (2.0x), R:R 2:1, trailing enabled, moderate position sizes (0.1)
- aggressive: ATR-based SL (1.5x), R:R 3:1, trailing enabled, larger position sizes (0.2)

Always include trailing stop for trend-following strategies. Use fixed_pips for scalping strategies."""


@router.post("/generate-strategy", response_model=AIStrategyResponse)
async def generate_strategy(
    request: AIStrategyRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Generate a trading strategy using AI based on natural language description."""
    
    # Ensure LLM client is initialized with database config
    if not llm_client._db_config_loaded:
        llm_client.reload_config(db)
    
    # Build the prompt
    indicators_text = ""
    if request.preferred_indicators:
        indicators_text = f"\nPreferred indicators to use: {', '.join(request.preferred_indicators)}"
    
    user_prompt = f"""Create a trading strategy based on this description:
"{request.prompt}"

Parameters:
- Symbol: {request.symbol}
- Timeframe: {request.timeframe}
- Risk Profile: {request.risk_profile}
{indicators_text}

Generate a complete strategy in JSON format as specified in the system prompt.
Return ONLY the JSON, no additional text."""

    try:
        reply, tokens = await llm_client.chat(
            [{"role": "user", "content": user_prompt}],
            STRATEGY_SYSTEM_PROMPT,
        )
        
        # Parse the JSON response
        import json
        import re
        
        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', reply)
        if json_match:
            strategy_data = json.loads(json_match.group())
        else:
            raise ValueError("No valid JSON found in response")
        
        # Create response
        strategy = GeneratedStrategy(
            id=str(uuid4()),
            name=strategy_data.get("name", "AI Generated Strategy"),
            description=strategy_data.get("description", request.prompt[:200]),
            strategy_type="ai_generated",
            code=strategy_data.get("code", "# No code generated"),
            parameters=[
                StrategyParameter(**p) for p in strategy_data.get("parameters", [])
            ],
            indicators=strategy_data.get("indicators", []),
            entry_rules=[
                StrategyRule(**r) for r in strategy_data.get("entry_rules", [])
            ],
            exit_rules=[
                StrategyRule(**r) for r in strategy_data.get("exit_rules", [])
            ],
            risk_management=RiskManagement(**strategy_data.get("risk_management", {})),
        )
        
        return AIStrategyResponse(
            strategy=strategy,
            explanation=strategy_data.get("explanation", "Strategy generated based on your description."),
            warnings=strategy_data.get("warnings", []),
            suggested_improvements=strategy_data.get("suggested_improvements", []),
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {e}")
        # Return a fallback strategy
        return create_fallback_strategy(request)
    except Exception as e:
        logger.error(f"Strategy generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate strategy: {str(e)}"
        )


@router.post("/generate-strategy-stream")
async def generate_strategy_stream(
    request: AIStrategyRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Generate a trading strategy with SSE streaming to prevent timeout.
    
    This endpoint sends keepalive events every 5 seconds while the LLM
    is generating the strategy. This prevents Render's 30-second timeout.
    
    Event types:
    - keepalive: Sent every 5 seconds to keep connection alive
    - progress: Sent with status updates
    - result: Final strategy JSON
    - error: Error message if generation fails
    """
    import json as json_module
    import re
    
    async def generate():
        # Send initial progress event
        yield f"event: progress\ndata: {{\"status\": \"Starting strategy generation...\"}}\n\n"
        
        # Ensure LLM client is initialized with database config
        if not llm_client._db_config_loaded:
            llm_client.reload_config(db)
        
        # Build the prompt
        indicators_text = ""
        if request.preferred_indicators:
            indicators_text = f"\nPreferred indicators to use: {', '.join(request.preferred_indicators)}"
        
        user_prompt = f"""Create a trading strategy based on this description:
"{request.prompt}"

Parameters:
- Symbol: {request.symbol}
- Timeframe: {request.timeframe}
- Risk Profile: {request.risk_profile}
{indicators_text}

Generate a complete strategy in JSON format as specified in the system prompt.
Return ONLY the JSON, no additional text."""

        yield f"event: progress\ndata: {{\"status\": \"Calling AI model...\"}}\n\n"
        
        # Run LLM call in background with keepalive
        llm_task = asyncio.create_task(
            llm_client.chat(
                [{"role": "user", "content": user_prompt}],
                STRATEGY_SYSTEM_PROMPT,
            )
        )
        
        # Send keepalive events while waiting for LLM
        keepalive_count = 0
        while not llm_task.done():
            await asyncio.sleep(5)  # Wait 5 seconds
            if not llm_task.done():
                keepalive_count += 1
                yield f"event: keepalive\ndata: {{\"count\": {keepalive_count}, \"message\": \"Still generating...\"}}\n\n"
        
        try:
            reply, tokens = await llm_task
            
            yield f"event: progress\ndata: {{\"status\": \"Parsing response...\"}}\n\n"
            
            # Parse the JSON response
            json_match = re.search(r'\{[\s\S]*\}', reply)
            if json_match:
                strategy_data = json_module.loads(json_match.group())
            else:
                raise ValueError("No valid JSON found in response")
            
            # Create response
            strategy = GeneratedStrategy(
                id=str(uuid4()),
                name=strategy_data.get("name", "AI Generated Strategy"),
                description=strategy_data.get("description", request.prompt[:200]),
                strategy_type="ai_generated",
                code=strategy_data.get("code", "# No code generated"),
                parameters=[
                    StrategyParameter(**p) for p in strategy_data.get("parameters", [])
                ],
                indicators=strategy_data.get("indicators", []),
                entry_rules=[
                    StrategyRule(**r) for r in strategy_data.get("entry_rules", [])
                ],
                exit_rules=[
                    StrategyRule(**r) for r in strategy_data.get("exit_rules", [])
                ],
                risk_management=RiskManagement(**strategy_data.get("risk_management", {})),
            )
            
            response = AIStrategyResponse(
                strategy=strategy,
                explanation=strategy_data.get("explanation", "Strategy generated based on your description."),
                warnings=strategy_data.get("warnings", []),
                suggested_improvements=strategy_data.get("suggested_improvements", []),
            )
            
            # Send final result
            yield f"event: result\ndata: {response.model_dump_json()}\n\n"
            
        except json_module.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            fallback = create_fallback_strategy(request)
            yield f"event: result\ndata: {fallback.model_dump_json()}\n\n"
        except Exception as e:
            logger.error(f"Strategy generation error: {e}")
            error_data = json_module.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


def create_fallback_strategy(request: AIStrategyRequest) -> AIStrategyResponse:
    """Create a fallback strategy when AI generation fails."""
    return AIStrategyResponse(
        strategy=GeneratedStrategy(
            id=str(uuid4()),
            name=f"{request.symbol} Strategy",
            description=request.prompt[:200],
            strategy_type="ai_generated",
            code="""# Fallback strategy template
def should_buy(data):
    rsi = calculate_rsi(data, 14)
    ema_fast = calculate_ema(data, 9)
    ema_slow = calculate_ema(data, 21)
    return rsi < 30 and ema_fast > ema_slow

def should_sell(data):
    rsi = calculate_rsi(data, 14)
    ema_fast = calculate_ema(data, 9)
    ema_slow = calculate_ema(data, 21)
    return rsi > 70 and ema_fast < ema_slow""",
            parameters=[
                StrategyParameter(name="rsi_period", type="number", default_value=14, description="RSI period"),
                StrategyParameter(name="ema_fast", type="number", default_value=9, description="Fast EMA period"),
                StrategyParameter(name="ema_slow", type="number", default_value=21, description="Slow EMA period"),
            ],
            indicators=["RSI", "EMA"],
            entry_rules=[
                StrategyRule(id="buy_1", condition="RSI < 30 AND EMA(9) > EMA(21)", action="BUY", description="Buy on oversold with trend"),
                StrategyRule(id="sell_1", condition="RSI > 70 AND EMA(9) < EMA(21)", action="SELL", description="Sell on overbought with trend"),
            ],
            exit_rules=[
                StrategyRule(id="exit_1", condition="hit_stop_loss OR hit_take_profit", action="CLOSE", description="Exit on SL/TP"),
            ],
            risk_management=RiskManagement(
                stop_loss_type="atr_based",
                stop_loss_value=2.0 if request.risk_profile == "moderate" else (2.5 if request.risk_profile == "conservative" else 1.5),
                take_profit_type="risk_reward",
                take_profit_value=2.0 if request.risk_profile == "moderate" else (1.5 if request.risk_profile == "conservative" else 3.0),
                trailing_stop=TrailingStopConfig(
                    enabled=True,
                    trailing_type="atr_based",
                    activation_pips=20 if request.risk_profile == "moderate" else (30 if request.risk_profile == "conservative" else 10),
                    trail_distance_pips=15,
                    atr_multiplier=1.5,
                    breakeven_enabled=True,
                    breakeven_pips=15 if request.risk_profile == "moderate" else (20 if request.risk_profile == "conservative" else 10),
                ),
                max_position_size=0.1 if request.risk_profile == "moderate" else (0.05 if request.risk_profile == "conservative" else 0.2),
                risk_per_trade_percent=2.0 if request.risk_profile == "moderate" else (1.0 if request.risk_profile == "conservative" else 3.0),
            ),
        ),
        explanation="This is a basic RSI + EMA crossover strategy with ATR-based risk management and trailing stop. AI generation encountered an issue, so a template strategy was provided.",
        warnings=[
            "This is a fallback template strategy",
            "AI generation was not fully successful",
            "Please refine and test before using",
        ],
        suggested_improvements=[
            "Add more confirmation indicators",
            "Consider adding time-based filters",
            "Test with different parameter values",
        ],
    )
