"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Sparkles,
  TrendingUp,
  Target,
  AlertCircle,
  CheckCircle2,
  Copy,
  ChevronRight,
  Bot,
  Activity,
  Star,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import Link from "next/link";

interface MLProfitableEURUSDCardProps {
  onClone?: () => void;
}

export function MLProfitableEURUSDCard({ onClone }: MLProfitableEURUSDCardProps) {
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Fetch default model for EURUSD
  const { data: defaultModel } = useQuery({
    queryKey: ["default-model", "EURUSD"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/ml-models/defaults/EURUSD`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
      });
      if (!res.ok) return null;
      return res.json();
    }
  });

  const handleClone = async () => {
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/strategies/templates/ml-profitable-eurusd/clone`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to clone strategy');
      }

      const strategy = await response.json();

      toast({
        title: "Strategy Created!",
        description: "ML Profitable EURUSD Strategy has been added to your library.",
      });

      // Call the onClone callback
      if (onClone) {
        onClone();
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to clone strategy",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="border-blue-500/20 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 hover:border-blue-500/40 transition-all duration-300">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Bot className="w-5 h-5 text-blue-500" />
              <CardTitle className="text-xl">ML Profitable EURUSD</CardTitle>
              <Badge variant="default" className="bg-blue-500/20 text-blue-500 border-blue-500/30">
                PROVEN
              </Badge>
              <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/30">
                EURUSD ONLY
              </Badge>
              {defaultModel && (
                <Badge
                  variant="outline"
                  className={defaultModel.is_user_override
                    ? "bg-purple-500/10 text-purple-400 border-purple-500/30"
                    : "bg-green-500/10 text-green-400 border-green-500/30"
                  }
                >
                  <Star className="w-3 h-3 mr-1" />
                  {defaultModel.is_user_override ? "Your Default" : "System Default"}
                </Badge>
              )}
            </div>
            <CardDescription className="text-slate-400">
              XGBoost-based strategy trained exclusively on EURUSD (Forex) - 79.1% win rate and 3.77 profit factor
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Performance Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
            <div className="text-xs text-slate-400 mb-1">Win Rate</div>
            <div className="text-xl font-bold text-green-400 flex items-center gap-1">
              <Target className="w-4 h-4" />
              79.1%
            </div>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
            <div className="text-xs text-slate-400 mb-1">Profit Factor</div>
            <div className="text-xl font-bold text-green-400 flex items-center gap-1">
              <TrendingUp className="w-4 h-4" />
              3.77
            </div>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
            <div className="text-xs text-slate-400 mb-1">Accuracy</div>
            <div className="text-xl font-bold text-blue-400 flex items-center gap-1">
              <Activity className="w-4 h-4" />
              60.3%
            </div>
          </div>

          <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
            <div className="text-xs text-slate-400 mb-1">Total Trades</div>
            <div className="text-xl font-bold text-green-400">4,675</div>
          </div>
        </div>

        {/* Configuration Details */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-slate-300">Strategy Configuration:</h4>

          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-blue-500" />
              <span className="text-slate-400 font-semibold">Trained on: EURUSD (Forex) Only</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-slate-400">ML Model: XGBoost Classifier (Forex-Optimized)</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-slate-400">Confidence Threshold: 70%</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-slate-400">Filters: Session + Volatility (forex-optimized)</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-slate-400">Risk Management: ATR-based (0.8:1.2 TP/SL)</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
              <span className="text-slate-400">Trading Hours: London/NY sessions</span>
            </div>
          </div>
        </div>

        {/* Expected Performance */}
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-slate-300">Expected Annual Performance:</h4>

          <div className="grid grid-cols-3 gap-3 text-xs">
            <div className="bg-slate-800/50 rounded p-2 border border-slate-700/50">
              <div className="text-slate-500 mb-1">0.01 lots</div>
              <div className="font-semibold text-slate-300">~$38/year</div>
            </div>
            <div className="bg-slate-800/50 rounded p-2 border border-slate-700/50">
              <div className="text-slate-500 mb-1">0.10 lots</div>
              <div className="font-semibold text-slate-300">~$380/year</div>
            </div>
            <div className="bg-slate-800/50 rounded p-2 border border-slate-700/50">
              <div className="text-slate-500 mb-1">1.00 lots</div>
              <div className="font-semibold text-slate-300">~$3,800/year</div>
            </div>
          </div>
        </div>

        {/* Symbol Warning */}
        <Alert className="bg-green-500/10 border-green-500/30">
          <AlertCircle className="h-4 w-4 text-green-500" />
          <AlertDescription className="text-xs text-slate-300">
            <strong>EURUSD Only:</strong> This model is trained exclusively on EURUSD (Forex) data.
            Using it for other symbols (XAUUSD, BTCUSD, etc.) will produce unreliable predictions.
            <Link href="/models" className="block mt-1 text-green-400 hover:text-green-300 underline">
              → Manage default models for all symbols
            </Link>
          </AlertDescription>
        </Alert>

        {/* Testing Warning */}
        <Alert className="bg-yellow-500/10 border-yellow-500/30">
          <AlertCircle className="h-4 w-4 text-yellow-500" />
          <AlertDescription className="text-xs text-slate-300">
            This is a proven profitable strategy. Always test on demo account for 30 days before going live. Start with 0.01 lots.
          </AlertDescription>
        </Alert>
      </CardContent>

      <CardFooter className="flex gap-3">
        <Button
          onClick={handleClone}
          disabled={isLoading}
          className="flex-1 bg-blue-500 hover:bg-blue-600 text-white"
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
              Cloning...
            </>
          ) : (
            <>
              <Copy className="w-4 h-4 mr-2" />
              Clone to My Strategies
            </>
          )}
        </Button>

        <Button
          variant="outline"
          className="border-slate-700 hover:bg-slate-800"
          onClick={() => window.open('/ML_AUTO_TRADING_GUIDE.md', '_blank')}
        >
          <Sparkles className="w-4 h-4 mr-2" />
          Learn More
          <ChevronRight className="w-4 h-4 ml-1" />
        </Button>
      </CardFooter>
    </Card>
  );
}
