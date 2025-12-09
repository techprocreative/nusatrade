"""AI Supervisor API with LLM integration."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
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
                provider = config["base_url"] or "OpenAI"
                logger.info(f"LLM client initialized (provider: {provider}, model: {config['model']})")
            except ImportError:
                logger.warning("openai package not installed")

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
                    model=settings.effective_llm_config["model"],
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
        conversation_id=conversation.id,
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
    """Get trading recommendations based on user's history."""
    # TODO: Fetch user's trade history and provide personalized recommendations
    
    prompt = """Based on general forex trading best practices, provide 3-5 actionable recommendations for improving trading performance. Focus on:
- Risk management
- Entry/exit timing
- Position sizing
- Emotional discipline"""

    reply, _ = await llm_client.chat(
        [{"role": "user", "content": prompt}],
        SYSTEM_PROMPTS["general"],
    )

    return {
        "recommendations": reply,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
