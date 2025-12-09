"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useGenerateStrategy } from "@/hooks/api/useStrategies";
import type { AIStrategyRequest, AIStrategyResponse } from "@/types";
import { Sparkles, Loader2 } from "lucide-react";

const SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD"];
const TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"];
const RISK_PROFILES = [
  { value: "conservative", label: "Conservative (Lower risk)" },
  { value: "moderate", label: "Moderate (Balanced)" },
  { value: "aggressive", label: "Aggressive (Higher risk)" },
];

const INDICATORS = [
  "RSI", "MACD", "EMA", "SMA", "Bollinger Bands",
  "Stochastic", "ATR", "ADX", "Ichimoku", "Fibonacci",
];

interface StrategyBuilderProps {
  onGenerated: (response: AIStrategyResponse) => void;
}

export function StrategyBuilder({ onGenerated }: StrategyBuilderProps) {
  const [prompt, setPrompt] = useState("");
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");
  const [riskProfile, setRiskProfile] = useState<"conservative" | "moderate" | "aggressive">("moderate");
  const [selectedIndicators, setSelectedIndicators] = useState<string[]>([]);

  const generateMutation = useGenerateStrategy();

  const toggleIndicator = (indicator: string) => {
    setSelectedIndicators((prev) =>
      prev.includes(indicator)
        ? prev.filter((i) => i !== indicator)
        : [...prev, indicator]
    );
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) return;

    const request: AIStrategyRequest = {
      prompt: prompt.trim(),
      symbol,
      timeframe,
      risk_profile: riskProfile,
      preferred_indicators: selectedIndicators.length > 0 ? selectedIndicators : undefined,
    };

    const response = await generateMutation.mutateAsync(request);
    onGenerated(response);
  };

  const examplePrompts = [
    "Create a trend following strategy using EMA crossover with RSI confirmation",
    "Build a scalping strategy for volatile market conditions using Bollinger Bands",
    "Design a mean reversion strategy that buys oversold conditions",
    "Create a breakout strategy that enters on support/resistance breaks",
  ];

  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-yellow-500" />
          AI Strategy Builder
        </CardTitle>
        <CardDescription>
          Describe your trading strategy in natural language and let AI generate it for you
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Strategy Description */}
        <div className="space-y-2">
          <Label htmlFor="prompt">Describe Your Strategy</Label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., Create a scalping strategy for EURUSD that uses RSI and EMA crossover. Enter when RSI is oversold and price crosses above EMA. Use tight stop loss and 1:2 risk reward ratio."
            className="w-full min-h-[120px] px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-muted-foreground">
            Be specific about entry/exit conditions, indicators, and risk management
          </p>
        </div>

        {/* Example Prompts */}
        <div className="space-y-2">
          <Label className="text-xs text-slate-400">Quick Examples</Label>
          <div className="flex flex-wrap gap-2">
            {examplePrompts.map((example, i) => (
              <Button
                key={i}
                type="button"
                variant="outline"
                size="sm"
                className="text-xs h-auto py-1.5 px-2"
                onClick={() => setPrompt(example)}
              >
                {example.slice(0, 40)}...
              </Button>
            ))}
          </div>
        </div>

        {/* Configuration */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="symbol">Symbol</Label>
            <Select value={symbol} onValueChange={setSymbol}>
              <SelectTrigger id="symbol">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SYMBOLS.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="timeframe">Timeframe</Label>
            <Select value={timeframe} onValueChange={setTimeframe}>
              <SelectTrigger id="timeframe">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIMEFRAMES.map((tf) => (
                  <SelectItem key={tf} value={tf}>{tf}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="risk">Risk Profile</Label>
            <Select value={riskProfile} onValueChange={(v: any) => setRiskProfile(v)}>
              <SelectTrigger id="risk">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RISK_PROFILES.map((rp) => (
                  <SelectItem key={rp.value} value={rp.value}>{rp.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Preferred Indicators */}
        <div className="space-y-2">
          <Label>Preferred Indicators (Optional)</Label>
          <div className="flex flex-wrap gap-2">
            {INDICATORS.map((indicator) => (
              <Button
                key={indicator}
                type="button"
                variant={selectedIndicators.includes(indicator) ? "default" : "outline"}
                size="sm"
                onClick={() => toggleIndicator(indicator)}
                className="h-8"
              >
                {indicator}
              </Button>
            ))}
          </div>
        </div>

        {/* Generate Button */}
        <Button
          onClick={handleGenerate}
          disabled={!prompt.trim() || generateMutation.isPending}
          className="w-full bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-700 hover:to-emerald-700"
          size="lg"
        >
          {generateMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Generating Strategy...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4 mr-2" />
              Generate Strategy with AI
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
