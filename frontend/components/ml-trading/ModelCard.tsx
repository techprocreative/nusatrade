"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Power,
  PowerOff,
  Link as LinkIcon,
  AlertTriangle,
  TrendingUp,
  Target,
  Star,
  Clock,
  Zap,
  CheckCircle2,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { StrategySelector } from "./StrategySelector";
import { activateModel, deactivateModel, type MLModel } from "@/lib/api/ml-models";

interface ModelCardProps {
  model: MLModel;
}

// Helper to get strategy type from model config
function getStrategyType(model: MLModel): string | null {
  if (model.config && typeof model.config === 'object') {
    return model.config.strategy_type || null;
  }
  return null;
}

// Check if model has built-in strategy (scalping models)
function hasBuiltInStrategy(model: MLModel): boolean {
  const strategyType = getStrategyType(model);
  return strategyType === 'ml_scalping' || strategyType === 'ml_profitable';
}

export function ModelCard({ model }: ModelCardProps) {
  const [showStrategySelector, setShowStrategySelector] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const token = typeof window !== 'undefined' ? localStorage.getItem("token") || "" : "";

  const strategyType = getStrategyType(model);
  const isScalping = strategyType === 'ml_scalping';
  const builtInStrategy = hasBuiltInStrategy(model);

  // Activate mutation
  const activateMutation = useMutation({
    mutationFn: () => activateModel(model.id, token),
    onSuccess: () => {
      toast({
        title: "Model Activated",
        description: `${model.name} is now active for auto-trading`,
      });
      queryClient.invalidateQueries({ queryKey: ["ml-models"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Activation Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Deactivate mutation
  const deactivateMutation = useMutation({
    mutationFn: () => deactivateModel(model.id, token),
    onSuccess: () => {
      toast({
        title: "Model Deactivated",
        description: `${model.name} is now inactive`,
      });
      queryClient.invalidateQueries({ queryKey: ["ml-models"] });
    },
  });

  const handleActivate = () => {
    // Built-in strategy models can activate directly
    if (builtInStrategy) {
      activateMutation.mutate();
      return;
    }

    if (!model.strategy_id) {
      toast({
        title: "Strategy Required",
        description: "Please link a strategy before activating",
        variant: "destructive",
      });
      setShowStrategySelector(true);
      return;
    }
    activateMutation.mutate();
  };

  const hasStrategy = !!model.strategy_id || builtInStrategy;
  const canActivate = hasStrategy && model.file_path;

  // Get metrics for display
  const metrics = model.performance_metrics || {};
  const winRate = metrics.win_rate;
  const accuracy = metrics.accuracy;
  const totalTrades = metrics.total_trades;
  const profitFactor = metrics.profit_factor;

  return (
    <>
      <Card className={model.is_active ? "border-green-500 border-2" : ""}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2">
                {model.name}
                {model.is_active && <Badge variant="default" className="bg-green-600">Active</Badge>}
                {isScalping && <Badge variant="outline" className="text-orange-500 border-orange-500">Scalping</Badge>}
              </CardTitle>
              <CardDescription className="flex items-center gap-2">
                <span>{model.symbol}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {model.timeframe}
                </span>
                <span>•</span>
                <span>{model.model_type}</span>
              </CardDescription>
            </div>
            {model.is_active ? (
              <Button
                variant="outline"
                size="icon"
                onClick={() => deactivateMutation.mutate()}
                disabled={deactivateMutation.isPending}
              >
                <PowerOff className="h-4 w-4 text-red-500" />
              </Button>
            ) : (
              <Button
                variant="outline"
                size="icon"
                onClick={handleActivate}
                disabled={!canActivate || activateMutation.isPending}
              >
                <Power className="h-4 w-4 text-green-500" />
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Performance Metrics */}
          {model.performance_metrics && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              {winRate !== undefined && (
                <div className="flex flex-col items-center p-2 bg-muted rounded-lg">
                  <TrendingUp className="h-4 w-4 text-green-500 mb-1" />
                  <span className="text-lg font-semibold">{winRate.toFixed(1)}%</span>
                  <span className="text-xs text-muted-foreground">Win Rate</span>
                </div>
              )}
              {accuracy !== undefined && (
                <div className="flex flex-col items-center p-2 bg-muted rounded-lg">
                  <Target className="h-4 w-4 text-blue-500 mb-1" />
                  <span className="text-lg font-semibold">{accuracy.toFixed(1)}%</span>
                  <span className="text-xs text-muted-foreground">Accuracy</span>
                </div>
              )}
              {totalTrades !== undefined && (
                <div className="flex flex-col items-center p-2 bg-muted rounded-lg">
                  <Zap className="h-4 w-4 text-yellow-500 mb-1" />
                  <span className="text-lg font-semibold">{totalTrades}</span>
                  <span className="text-xs text-muted-foreground">Trades</span>
                </div>
              )}
              {profitFactor !== undefined && (
                <div className="flex flex-col items-center p-2 bg-muted rounded-lg">
                  <Star className="h-4 w-4 text-purple-500 mb-1" />
                  <span className="text-lg font-semibold">{profitFactor.toFixed(2)}</span>
                  <span className="text-xs text-muted-foreground">Profit Factor</span>
                </div>
              )}
            </div>
          )}

          {/* Strategy Status */}
          {builtInStrategy ? (
            <Alert className="border-green-500/50 bg-green-500/10">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <AlertDescription>
                <strong>Built-in Strategy:</strong>{" "}
                {isScalping ? "ML Scalping (TP 5 pips, SL 8 pips)" : "ML Profitable"}
              </AlertDescription>
            </Alert>
          ) : hasStrategy && model.strategy_name ? (
            <Alert>
              <LinkIcon className="h-4 w-4" />
              <AlertDescription>
                Linked to: <strong>{model.strategy_name}</strong>
              </AlertDescription>
            </Alert>
          ) : (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                No strategy linked. Required for activation.
              </AlertDescription>
            </Alert>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            {!hasStrategy && (
              <Button
                variant="outline"
                className="w-full"
                onClick={() => setShowStrategySelector(true)}
              >
                <LinkIcon className="mr-2 h-4 w-4" />
                Link Strategy
              </Button>
            )}
            {hasStrategy && !model.is_active && (
              <Button
                className="w-full"
                onClick={handleActivate}
                disabled={activateMutation.isPending}
              >
                <Power className="mr-2 h-4 w-4" />
                Activate for Auto-Trading
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <StrategySelector
        model={model}
        open={showStrategySelector}
        onClose={() => setShowStrategySelector(false)}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ["ml-models"] })}
      />
    </>
  );
}

