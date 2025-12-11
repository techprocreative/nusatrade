"use client";

import { useState } from "react";
import { useBacktestStrategies, useRunBacktest, useBacktestResult, useStrategies } from "@/hooks/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className={`text-2xl font-bold ${color || ""}`}>{value}</p>
      </CardContent>
    </Card>
  );
}

export default function BacktestPage() {
  const [config, setConfig] = useState({
    symbol: "EURUSD",
    strategy: "ma_crossover",
    timeframe: "H1",
    start_date: "2024-01-01",
    end_date: "2024-12-01",
    initial_balance: 10000,
    lot_size: 0.1,
  });
  const [sessionId, setSessionId] = useState<string | null>(null);

  // API hooks
  const { data: presetStrategies = [] } = useBacktestStrategies();
  const { data: userStrategies = [] } = useStrategies();
  const runBacktestMutation = useRunBacktest();
  const { data: sessionData, isLoading: loadingResult } = useBacktestResult(sessionId);

  // Extract metrics from session result - backend returns SessionResponse with nested result
  const sessionAny = sessionData as any;
  const metrics = sessionAny?.result || sessionAny;
  const trades = sessionAny?.trades || sessionAny?.result?.trades || [];

  // Combine preset and user strategies
  const allStrategies = [
    ...presetStrategies,
    ...userStrategies.map((s: any) => ({ id: s.id, name: s.name, type: 'user' })),
  ];

  const SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"];
  const TIMEFRAMES = ["M15", "M30", "H1", "H4", "D1"];

  const handleRunBacktest = async () => {
    const response = await runBacktestMutation.mutateAsync({
      symbol: config.symbol,
      strategy_id: config.strategy,
      timeframe: config.timeframe,
      start_date: config.start_date,
      end_date: config.end_date,
      initial_balance: config.initial_balance,
    });

    if (response.session_id) {
      setSessionId(response.session_id);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Backtesting</h1>
        <p className="text-muted-foreground mt-1">
          Test your trading strategies on historical data
        </p>
      </div>

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="symbol">Symbol</Label>
              <Select
                value={config.symbol}
                onValueChange={(value) => setConfig({ ...config, symbol: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SYMBOLS.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="strategy">Strategy</Label>
              <Select
                value={config.strategy}
                onValueChange={(value) => setConfig({ ...config, strategy: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {allStrategies.length > 0 ? (
                    allStrategies.map((strat: any) => (
                      <SelectItem key={strat.id} value={strat.id}>
                        {strat.name} {strat.type === 'user' && '(Custom)'}
                      </SelectItem>
                    ))
                  ) : (
                    <>
                      <SelectItem value="ma_crossover">MA Crossover</SelectItem>
                      <SelectItem value="rsi">RSI Strategy</SelectItem>
                      <SelectItem value="macd">MACD Strategy</SelectItem>
                    </>
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="timeframe">Timeframe</Label>
              <Select
                value={config.timeframe}
                onValueChange={(value) => setConfig({ ...config, timeframe: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIMEFRAMES.map((tf) => (
                    <SelectItem key={tf} value={tf}>
                      {tf}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="lotSize">Lot Size</Label>
              <Input
                id="lotSize"
                type="number"
                step="0.01"
                min="0.01"
                value={config.lot_size}
                onChange={(e) =>
                  setConfig({ ...config, lot_size: parseFloat(e.target.value) })
                }
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="startDate">Start Date</Label>
              <Input
                id="startDate"
                type="date"
                value={config.start_date}
                onChange={(e) => setConfig({ ...config, start_date: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="endDate">End Date</Label>
              <Input
                id="endDate"
                type="date"
                value={config.end_date}
                onChange={(e) => setConfig({ ...config, end_date: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="balance">Initial Balance</Label>
              <Input
                id="balance"
                type="number"
                step="1000"
                min="1000"
                value={config.initial_balance}
                onChange={(e) =>
                  setConfig({ ...config, initial_balance: parseFloat(e.target.value) })
                }
              />
            </div>
          </div>

          <Button
            onClick={handleRunBacktest}
            disabled={runBacktestMutation.isPending || loadingResult}
            className="mt-6 w-full md:w-auto"
          >
            {runBacktestMutation.isPending || loadingResult
              ? "Running Backtest..."
              : "Run Backtest"}
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {metrics && (metrics.total_trades || metrics.net_profit !== undefined) && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="Total Trades"
              value={metrics.total_trades?.toString() || '0'}
            />
            <MetricCard
              label="Win Rate"
              value={`${(metrics.win_rate ?? 0).toFixed(1)}%`}
              color={(metrics.win_rate ?? 0) >= 50 ? "text-green-500" : "text-red-500"}
            />
            <MetricCard
              label="Net Profit"
              value={`$${(metrics.net_profit ?? 0).toFixed(2)}`}
              color={(metrics.net_profit ?? 0) >= 0 ? "text-green-500" : "text-red-500"}
            />
            <MetricCard
              label="Profit Factor"
              value={(metrics.profit_factor ?? 0).toFixed(2)}
              color={(metrics.profit_factor ?? 0) >= 1 ? "text-green-500" : "text-red-500"}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <MetricCard
              label="Max Drawdown"
              value={`${(metrics.max_drawdown_pct ?? 0).toFixed(1)}%`}
              color="text-red-500"
            />
            <MetricCard
              label="Sharpe Ratio"
              value={(metrics.sharpe_ratio ?? 0).toFixed(2)}
            />
            <MetricCard
              label="Winning Trades"
              value={`${metrics.winning_trades ?? 0}/${metrics.total_trades ?? 0}`}
            />
          </div>

          {/* Trades Table */}
          <Card>
            <CardHeader>
              <CardTitle>Trades ({trades?.length || 0})</CardTitle>
            </CardHeader>
            <CardContent>
              {trades && trades.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-muted-foreground border-b">
                        <th className="text-left py-2">Symbol</th>
                        <th className="text-left py-2">Type</th>
                        <th className="text-right py-2">Entry</th>
                        <th className="text-right py-2">Exit</th>
                        <th className="text-right py-2">Profit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trades.slice(0, 20).map((trade: any, index: number) => (
                        <tr key={trade.id || index} className="border-b border-border/50">
                          <td className="py-3">{trade.symbol}</td>
                          <td
                            className={
                              trade.order_type === "BUY" ? "text-green-500" : "text-red-500"
                            }
                          >
                            {trade.order_type}
                          </td>
                          <td className="text-right text-muted-foreground">
                            {trade.entry_price?.toFixed(5) || '-'}
                          </td>
                          <td className="text-right text-muted-foreground">
                            {trade.exit_price?.toFixed(5) || '-'}
                          </td>
                          <td
                            className={`text-right font-semibold ${(trade.profit ?? 0) >= 0 ? "text-green-500" : "text-red-500"
                              }`}
                          >
                            ${(trade.profit ?? 0).toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-center py-8 text-muted-foreground">No trades executed</p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
