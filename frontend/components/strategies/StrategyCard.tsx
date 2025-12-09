"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useDeleteStrategy, useToggleStrategy } from "@/hooks/api/useStrategies";
import type { TradingStrategy } from "@/types";
import {
  Bot,
  Sparkles,
  Settings2,
  Play,
  Pause,
  Trash2,
  TestTube2,
  MoreVertical,
  TrendingUp,
  TrendingDown,
} from "lucide-react";

interface StrategyCardProps {
  strategy: TradingStrategy;
  onSelect?: (strategy: TradingStrategy) => void;
  onBacktest?: (strategy: TradingStrategy) => void;
}

export function StrategyCard({ strategy, onSelect, onBacktest }: StrategyCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const deleteMutation = useDeleteStrategy();
  const toggleMutation = useToggleStrategy();

  const handleDelete = async () => {
    await deleteMutation.mutateAsync(strategy.id);
    setShowDeleteConfirm(false);
  };

  const handleToggle = async () => {
    await toggleMutation.mutateAsync({
      id: strategy.id,
      isActive: !strategy.is_active,
    });
  };

  const getTypeIcon = () => {
    switch (strategy.strategy_type) {
      case 'ai_generated': return <Sparkles className="w-4 h-4 text-yellow-500" />;
      case 'custom': return <Settings2 className="w-4 h-4 text-blue-500" />;
      case 'preset': return <Bot className="w-4 h-4 text-purple-500" />;
    }
  };

  const getTypeLabel = () => {
    switch (strategy.strategy_type) {
      case 'ai_generated': return 'AI Generated';
      case 'custom': return 'Custom';
      case 'preset': return 'Preset';
    }
  };

  const hasBacktestResults = strategy.backtest_results !== undefined;
  const winRate = strategy.backtest_results?.win_rate ?? 0;
  const netProfit = strategy.backtest_results?.net_profit ?? 0;

  return (
    <>
      <Card className="bg-slate-800 border-slate-700 hover:border-slate-600 transition-colors">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3 flex-1 min-w-0">
              {/* Status Indicator */}
              <div
                className={`w-3 h-3 rounded-full mt-1.5 flex-shrink-0 ${
                  strategy.is_active ? "bg-green-500" : "bg-slate-600"
                }`}
              />

              {/* Strategy Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3
                    className="font-semibold text-white truncate cursor-pointer hover:text-blue-400"
                    onClick={() => onSelect?.(strategy)}
                  >
                    {strategy.name}
                  </h3>
                  <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-slate-700 rounded-full flex-shrink-0">
                    {getTypeIcon()}
                    {getTypeLabel()}
                  </span>
                </div>

                <p className="text-sm text-slate-400 line-clamp-2 mb-2">
                  {strategy.description}
                </p>

                {/* Indicators */}
                <div className="flex flex-wrap gap-1 mb-3">
                  {strategy.indicators.slice(0, 4).map((indicator, i) => (
                    <span
                      key={i}
                      className="px-1.5 py-0.5 text-xs bg-slate-700/50 text-slate-300 rounded"
                    >
                      {indicator}
                    </span>
                  ))}
                  {strategy.indicators.length > 4 && (
                    <span className="px-1.5 py-0.5 text-xs bg-slate-700/50 text-slate-400 rounded">
                      +{strategy.indicators.length - 4}
                    </span>
                  )}
                </div>

                {/* Backtest Results */}
                {hasBacktestResults && (
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1">
                      {winRate >= 50 ? (
                        <TrendingUp className="w-3 h-3 text-green-500" />
                      ) : (
                        <TrendingDown className="w-3 h-3 text-red-500" />
                      )}
                      <span className={winRate >= 50 ? "text-green-400" : "text-red-400"}>
                        {winRate.toFixed(1)}% Win
                      </span>
                    </div>
                    <div className={netProfit >= 0 ? "text-green-400" : "text-red-400"}>
                      {netProfit >= 0 ? '+' : ''}${netProfit.toFixed(0)}
                    </div>
                    <div className="text-slate-500">
                      {strategy.backtest_results?.total_trades} trades
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1 flex-shrink-0">
              <Button
                size="sm"
                variant="ghost"
                onClick={handleToggle}
                disabled={toggleMutation.isPending}
                className={strategy.is_active ? "text-green-400" : "text-slate-400"}
              >
                {strategy.is_active ? (
                  <Pause className="w-4 h-4" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
              </Button>

              {onBacktest && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onBacktest(strategy)}
                  className="text-slate-400 hover:text-white"
                >
                  <TestTube2 className="w-4 h-4" />
                </Button>
              )}

              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowDeleteConfirm(true)}
                disabled={deleteMutation.isPending}
                className="text-slate-400 hover:text-red-400"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={showDeleteConfirm}
        onOpenChange={setShowDeleteConfirm}
        title="Delete Strategy"
        description={`Are you sure you want to delete "${strategy.name}"? This action cannot be undone.`}
        confirmText="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteMutation.isPending}
      />
    </>
  );
}
