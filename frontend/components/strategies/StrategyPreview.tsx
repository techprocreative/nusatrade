"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useSaveStrategy, useQuickBacktest } from "@/hooks/api/useStrategies";
import type { AIStrategyResponse, TradingStrategy, BacktestMetrics } from "@/types";
import {
  ArrowUpCircle,
  ArrowDownCircle,
  XCircle,
  AlertTriangle,
  Lightbulb,
  Code,
  TestTube2,
  Save,
  Loader2,
  CheckCircle2,
} from "lucide-react";

interface StrategyPreviewProps {
  response: AIStrategyResponse;
  onSaved?: () => void;
  onClear?: () => void;
}

export function StrategyPreview({ response, onSaved, onClear }: StrategyPreviewProps) {
  const { strategy, explanation, warnings, suggested_improvements } = response;
  const [name, setName] = useState(strategy.name);
  const [showCode, setShowCode] = useState(false);
  const [backtestResult, setBacktestResult] = useState<BacktestMetrics | null>(null);

  const saveMutation = useSaveStrategy();
  const backtestMutation = useQuickBacktest();

  const handleSave = async () => {
    await saveMutation.mutateAsync({
      name,
      description: strategy.description,
      strategy_type: 'ai_generated',
      code: strategy.code,
      parameters: strategy.parameters,
      indicators: strategy.indicators,
      entry_rules: strategy.entry_rules,
      exit_rules: strategy.exit_rules,
      risk_management: strategy.risk_management,
    });
    onSaved?.();
  };

  const handleQuickBacktest = async () => {
    if (!strategy.id) return;
    const result = await backtestMutation.mutateAsync({
      strategy_id: strategy.id,
      symbol: 'EURUSD',
      timeframe: 'H1',
      days: 30,
    });
    setBacktestResult(result);
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'BUY': return <ArrowUpCircle className="w-4 h-4 text-green-500" />;
      case 'SELL': return <ArrowDownCircle className="w-4 h-4 text-red-500" />;
      case 'CLOSE': return <XCircle className="w-4 h-4 text-yellow-500" />;
      default: return null;
    }
  };

  return (
    <div className="space-y-4">
      {/* Strategy Header */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1 flex-1">
              <Label htmlFor="strategyName" className="text-xs text-slate-400">Strategy Name</Label>
              <Input
                id="strategyName"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="text-xl font-bold bg-transparent border-none p-0 h-auto focus-visible:ring-0"
              />
              <CardDescription>{strategy.description}</CardDescription>
            </div>
            <span className="px-2 py-1 text-xs bg-blue-500/20 text-blue-400 rounded-full">
              AI Generated
            </span>
          </div>
        </CardHeader>
      </Card>

      {/* Explanation */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-yellow-500" />
            AI Explanation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-300 whitespace-pre-wrap">{explanation}</p>
        </CardContent>
      </Card>

      {/* Indicators & Parameters */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Indicators Used</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {strategy.indicators.map((indicator, i) => (
                <span key={i} className="px-2 py-1 text-xs bg-slate-700 rounded-full">
                  {indicator}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Parameters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {strategy.parameters.map((param, i) => (
                <div key={i} className="flex justify-between text-sm">
                  <span className="text-slate-400">{param.name}</span>
                  <span className="text-white">{String(param.default_value)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Entry & Exit Rules */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-green-400">Entry Rules</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {strategy.entry_rules.map((rule, i) => (
              <div key={i} className="p-3 bg-slate-700/50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  {getActionIcon(rule.action)}
                  <span className="font-medium text-sm">{rule.action}</span>
                </div>
                <p className="text-xs text-slate-400">{rule.description}</p>
                <code className="text-xs text-slate-300 mt-1 block">{rule.condition}</code>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-red-400">Exit Rules</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {strategy.exit_rules.map((rule, i) => (
              <div key={i} className="p-3 bg-slate-700/50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  {getActionIcon(rule.action)}
                  <span className="font-medium text-sm">{rule.action}</span>
                </div>
                <p className="text-xs text-slate-400">{rule.description}</p>
                <code className="text-xs text-slate-300 mt-1 block">{rule.condition}</code>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Risk Management */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Risk Management</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-slate-400">Stop Loss</p>
              <p className="font-semibold">
                {strategy.risk_management.stop_loss_value}{' '}
                <span className="text-xs text-slate-400">
                  ({strategy.risk_management.stop_loss_type})
                </span>
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Take Profit</p>
              <p className="font-semibold">
                {strategy.risk_management.take_profit_value}{' '}
                <span className="text-xs text-slate-400">
                  ({strategy.risk_management.take_profit_type})
                </span>
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Max Position Size</p>
              <p className="font-semibold">{strategy.risk_management.max_position_size} lots</p>
            </div>
            {strategy.risk_management.max_daily_loss && (
              <div>
                <p className="text-xs text-slate-400">Max Daily Loss</p>
                <p className="font-semibold">${strategy.risk_management.max_daily_loss}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Warnings */}
      {warnings.length > 0 && (
        <Card className="bg-yellow-500/10 border-yellow-500/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2 text-yellow-400">
              <AlertTriangle className="w-4 h-4" />
              Warnings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc list-inside space-y-1 text-sm text-yellow-300">
              {warnings.map((warning, i) => (
                <li key={i}>{warning}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Suggestions */}
      {suggested_improvements.length > 0 && (
        <Card className="bg-blue-500/10 border-blue-500/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2 text-blue-400">
              <Lightbulb className="w-4 h-4" />
              Suggested Improvements
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc list-inside space-y-1 text-sm text-blue-300">
              {suggested_improvements.map((suggestion, i) => (
                <li key={i}>{suggestion}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Quick Backtest Results */}
      {backtestResult && (
        <Card className="bg-emerald-500/10 border-emerald-500/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              Quick Backtest Results (30 days)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-slate-400">Win Rate</p>
                <p className={`font-bold ${backtestResult.win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                  {backtestResult.win_rate.toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Net Profit</p>
                <p className={`font-bold ${backtestResult.net_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  ${backtestResult.net_profit.toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Total Trades</p>
                <p className="font-bold">{backtestResult.total_trades}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Profit Factor</p>
                <p className={`font-bold ${backtestResult.profit_factor >= 1 ? 'text-green-400' : 'text-red-400'}`}>
                  {backtestResult.profit_factor.toFixed(2)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        <Button
          variant="outline"
          onClick={() => setShowCode(true)}
        >
          <Code className="w-4 h-4 mr-2" />
          View Code
        </Button>

        {strategy.id && (
          <Button
            variant="outline"
            onClick={handleQuickBacktest}
            disabled={backtestMutation.isPending}
          >
            {backtestMutation.isPending ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <TestTube2 className="w-4 h-4 mr-2" />
            )}
            Quick Backtest
          </Button>
        )}

        <Button
          onClick={handleSave}
          disabled={saveMutation.isPending || !name.trim()}
          className="bg-gradient-to-r from-blue-600 to-emerald-600"
        >
          {saveMutation.isPending ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          Save Strategy
        </Button>

        {onClear && (
          <Button variant="ghost" onClick={onClear}>
            Clear & Start Over
          </Button>
        )}
      </div>

      {/* Code Dialog */}
      <Dialog open={showCode} onOpenChange={setShowCode}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Strategy Code</DialogTitle>
            <DialogDescription>
              Generated strategy logic in Python-like pseudocode
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-auto">
            <pre className="p-4 bg-slate-900 rounded-lg text-sm text-slate-300 overflow-auto">
              <code>{strategy.code}</code>
            </pre>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCode(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
