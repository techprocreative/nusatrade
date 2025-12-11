"use client";

import { useState } from "react";
import { useBacktestStrategies, useRunBacktest, useBacktestSessions, useStrategies } from "@/hooks/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { BacktestResult, BacktestTrade, BacktestSession } from "@/types";
import { Play, History, TrendingUp, TrendingDown, Calendar, Clock } from "lucide-react";

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

function BacktestResultDisplay({ result, trades }: { result: BacktestResult; trades: BacktestTrade[] }) {
  const totalTrades = result.total_trades ?? 0;
  const winRate = result.win_rate ?? 0;
  // Calculate winning trades from win_rate if not available (for legacy data)
  const winningTrades = result.winning_trades ?? Math.round((winRate / 100) * totalTrades);
  
  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Total Trades"
          value={totalTrades.toString()}
        />
        <MetricCard
          label="Win Rate"
          value={`${winRate.toFixed(1)}%`}
          color={winRate >= 50 ? "text-green-500" : "text-red-500"}
        />
        <MetricCard
          label="Net Profit"
          value={`$${(result.net_profit ?? 0).toFixed(2)}`}
          color={(result.net_profit ?? 0) >= 0 ? "text-green-500" : "text-red-500"}
        />
        <MetricCard
          label="Profit Factor"
          value={(result.profit_factor ?? 0).toFixed(2)}
          color={(result.profit_factor ?? 0) >= 1 ? "text-green-500" : "text-red-500"}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          label="Max Drawdown"
          value={`${(result.max_drawdown_pct ?? 0).toFixed(1)}%`}
          color="text-red-500"
        />
        <MetricCard
          label="Sharpe Ratio"
          value={(result.sharpe_ratio ?? 0).toFixed(2)}
        />
        <MetricCard
          label="Winning Trades"
          value={`${winningTrades}/${totalTrades}`}
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
                  {trades.slice(0, 20).map((trade, index) => (
                    <tr key={index} className="border-b border-border/50">
                      <td className="py-3">{trade.symbol}</td>
                      <td className={trade.order_type === "BUY" ? "text-green-500" : "text-red-500"}>
                        {trade.order_type}
                      </td>
                      <td className="text-right text-muted-foreground">
                        {trade.entry_price?.toFixed(5) || '-'}
                      </td>
                      <td className="text-right text-muted-foreground">
                        {trade.exit_price?.toFixed(5) || '-'}
                      </td>
                      <td className={`text-right font-semibold ${(trade.profit ?? 0) >= 0 ? "text-green-500" : "text-red-500"}`}>
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
  );
}

function HistoryItem({ 
  session, 
  onSelect, 
  isSelected 
}: { 
  session: BacktestSession; 
  onSelect: (session: BacktestSession) => void;
  isSelected: boolean;
}) {
  const netProfit = session.result?.net_profit ?? 0;
  const winRate = session.result?.win_rate ?? 0;
  const totalTrades = session.result?.total_trades ?? 0;
  
  return (
    <Card 
      className={`cursor-pointer transition-colors hover:bg-accent ${isSelected ? 'border-primary bg-accent' : ''}`}
      onClick={() => onSelect(session)}
    >
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold">{session.symbol}</span>
              <Badge variant="outline">{session.timeframe}</Badge>
              <Badge variant={session.status === 'completed' ? 'default' : session.status === 'failed' ? 'destructive' : 'secondary'}>
                {session.status}
              </Badge>
            </div>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {session.start_date} - {session.end_date}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(session.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
          
          {session.status === 'completed' && session.result && (
            <div className="text-right">
              <div className={`flex items-center gap-1 font-semibold ${netProfit >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {netProfit >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                ${netProfit.toFixed(2)}
              </div>
              <div className="text-sm text-muted-foreground">
                {winRate.toFixed(1)}% Win | {totalTrades} trades
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function BacktestPage() {
  const [activeTab, setActiveTab] = useState("run");
  const [config, setConfig] = useState({
    symbol: "EURUSD",
    strategy: "ma_crossover",
    timeframe: "H1",
    start_date: "2024-01-01",
    end_date: "2024-12-01",
    initial_balance: 10000,
    lot_size: 0.1,
  });
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [selectedSession, setSelectedSession] = useState<BacktestSession | null>(null);

  // API hooks
  const { data: presetStrategies = [] } = useBacktestStrategies();
  const { data: userStrategies = [] } = useStrategies();
  const { data: sessions = [], isLoading: loadingSessions } = useBacktestSessions();
  const runBacktestMutation = useRunBacktest();

  // Get trades from result
  const currentTrades: BacktestTrade[] = backtestResult?.trades || [];
  const selectedTrades: BacktestTrade[] = selectedSession?.result?.trades || [];

  // Combine preset and user strategies
  const allStrategies = [
    ...presetStrategies,
    ...userStrategies.map((s: any) => ({ id: s.id, name: s.name, type: 'user' })),
  ];

  const SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"];
  const TIMEFRAMES = ["M15", "M30", "H1", "H4", "D1"];

  const handleRunBacktest = async () => {
    setBacktestResult(null);
    const response = await runBacktestMutation.mutateAsync({
      symbol: config.symbol,
      strategy_id: config.strategy,
      timeframe: config.timeframe,
      start_date: config.start_date,
      end_date: config.end_date,
      initial_balance: config.initial_balance,
      lot_size: config.lot_size,
    });

    if (response) {
      setBacktestResult(response as BacktestResult);
    }
  };

  const handleSelectSession = (session: BacktestSession) => {
    setSelectedSession(session);
  };

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Backtesting</h1>
        <p className="text-muted-foreground mt-1">
          Test your trading strategies on historical data
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="run" className="flex items-center gap-2">
            <Play className="w-4 h-4" />
            Run Backtest
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <History className="w-4 h-4" />
            History ({sessions.length})
          </TabsTrigger>
        </TabsList>

        {/* Run Backtest Tab */}
        <TabsContent value="run" className="space-y-6">
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
                disabled={runBacktestMutation.isPending}
                className="mt-6 w-full md:w-auto"
              >
                {runBacktestMutation.isPending
                  ? "Running Backtest..."
                  : "Run Backtest"}
              </Button>
            </CardContent>
          </Card>

          {/* Current Results */}
          {backtestResult && (backtestResult.total_trades || backtestResult.net_profit !== undefined) && (
            <BacktestResultDisplay result={backtestResult} trades={currentTrades} />
          )}
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Sessions List */}
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Backtest Sessions</h3>
              {loadingSessions ? (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    Loading sessions...
                  </CardContent>
                </Card>
              ) : sessions.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    No backtest history yet. Run your first backtest!
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
                  {sessions.map((session) => (
                    <HistoryItem
                      key={session.id}
                      session={session}
                      onSelect={handleSelectSession}
                      isSelected={selectedSession?.id === session.id}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Selected Session Details */}
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Session Details</h3>
              {selectedSession ? (
                selectedSession.result ? (
                  <div className="space-y-4">
                    <Card>
                      <CardContent className="pt-6">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-muted-foreground">Symbol</p>
                            <p className="font-semibold">{selectedSession.symbol}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Timeframe</p>
                            <p className="font-semibold">{selectedSession.timeframe}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Period</p>
                            <p className="font-semibold">{selectedSession.start_date} - {selectedSession.end_date}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Initial Balance</p>
                            <p className="font-semibold">${selectedSession.initial_balance.toLocaleString()}</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                    <BacktestResultDisplay result={selectedSession.result} trades={selectedTrades} />
                  </div>
                ) : (
                  <Card>
                    <CardContent className="py-8 text-center text-muted-foreground">
                      No results available for this session
                    </CardContent>
                  </Card>
                )
              ) : (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    Select a session from the list to view details
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
