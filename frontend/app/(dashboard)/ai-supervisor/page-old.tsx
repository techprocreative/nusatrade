"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function AISupervisorPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "Hello! I'm your AI Trading Supervisor. I can help you with:\n\n• Analyzing market conditions\n• Reviewing your trading performance\n• Explaining trading concepts\n• Providing strategy recommendations\n\nHow can I assist you today?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      await new Promise((r) => setTimeout(r, 1500));

      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: generateResponse(userMessage.content),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiResponse]);
    } catch (error) {
      console.error("Failed to get AI response:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const quickActions = [
    "Analyze EURUSD today",
    "What's my risk exposure?",
    "Suggest entry points",
    "Review my last trades",
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-white">AI Supervisor</h1>
        <span className="px-3 py-1 bg-green-600/20 text-green-400 rounded-full text-sm">
          Online
        </span>
      </div>

      <div className="flex-1 bg-slate-800 rounded-lg border border-slate-700 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-4 ${message.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-slate-700 text-slate-100"
                  }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                <p className="text-xs opacity-50 mt-2">
                  {message.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-700 rounded-lg p-4">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="px-4 py-2 border-t border-slate-700">
          <div className="flex gap-2 overflow-x-auto pb-2">
            {quickActions.map((action) => (
              <button
                key={action}
                onClick={() => setInput(action)}
                className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded-full text-sm text-slate-300 whitespace-nowrap"
              >
                {action}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-4 border-t border-slate-700">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me anything about trading..."
              className="flex-1 px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-white font-semibold"
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function generateResponse(query: string): string {
  const q = query.toLowerCase();

  if (q.includes("eurusd") || q.includes("eur/usd")) {
    return "Based on current market conditions for EUR/USD:\n\n📊 Technical Analysis:\n• Current trend: Slightly bullish\n• RSI (14): 55 - Neutral zone\n• MACD: Bullish crossover forming\n\n📍 Key Levels:\n• Resistance: 1.0950, 1.1000\n• Support: 1.0850, 1.0800\n\n💡 Recommendation: Consider long positions on pullbacks to 1.0870-1.0880 with stops below 1.0840.";
  }

  if (q.includes("risk")) {
    return "📊 Current Risk Analysis:\n\n• Open positions: 2\n• Total exposure: 0.3 lots\n• Account risk: 1.8% of equity\n• Max drawdown today: 0.5%\n\n✅ Your risk management looks healthy. You're staying within the recommended 2% risk per trade.";
  }

  if (q.includes("entry") || q.includes("suggest")) {
    return "🎯 Potential Entry Points:\n\nEUR/USD (Long)\n• Entry: 1.0875\n• Stop Loss: 1.0845\n• Take Profit: 1.0935\n• Risk/Reward: 1:2\n\nGBP/USD (Short)\n• Entry: 1.2680\n• Stop Loss: 1.2720\n• Take Profit: 1.2600\n• Risk/Reward: 1:2\n\n⚠️ Always confirm with your own analysis before entering trades.";
  }

  if (q.includes("review") || q.includes("trade")) {
    return "📈 Recent Trading Performance:\n\n• Win Rate: 62% (last 30 days)\n• Profit Factor: 1.75\n• Average Win: $45.50\n• Average Loss: $26.00\n\n💡 Observations:\n• Your best performing pair is EUR/USD\n• Consider tightening stops on losing trades\n• Morning sessions show better results";
  }

  return "I understand your question. Let me provide some insights:\n\nTo give you the most accurate analysis, I would need:\n1. The specific currency pair you're interested in\n2. Your preferred timeframe\n3. Your current positions (if any)\n\nFeel free to ask about:\n• Market analysis for any forex pair\n• Risk management review\n• Strategy recommendations\n• Trade performance analysis";
}
