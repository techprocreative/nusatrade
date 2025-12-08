"use client";

import { useState } from "react";

interface BacktestResult {
  metrics: {
    total_trades: number;
    winning_trades: number;
    net_profit: number;
    win_rate: number;
    profit_factor: number;
    max_drawdown_pct: number;
    sharpe_ratio: number;
  };
  trades: Array<{
    id: number;
    symbol: string;
    order_type: string;
    entry_price: number;
    exit_price: number;
    profit: number;
  }>;
}

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("EURUSD");
  const [strategy, setStrategy] = useState("ma_crossover");
  const [timeframe, setTimeframe] = useState("H1");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2024-12-01");
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const strategies = [
    { id: "ma_crossover", name: "MA Crossover" },
    { id: "rsi", name: "RSI Strategy" },
    { id: "macd", name: "MACD Strategy" },
    { id: "bollinger", name: "Bollinger Bands" },
  ];

  const timeframes = ["M15", "M30", "H1", "H4", "D1"];
  const symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"];

  const handleRunBacktest = async () => {
    setIsRunning(true);
    setResult(null);

    try {
      await new Promise((r) => setTimeout(r, 2000));

      setResult({
        metrics: {
          total_trades: 156,
          winning_trades: 94,
          net_profit: 2847.5,
          win_rate: 60.26,
          profit_factor: 1.85,
          max_drawdown_pct: 12.4,
          sharpe_ratio: 1.42,
        },
        trades: [
          { id: 1, symbol: "EURUSD", order_type: "BUY", entry_price: 1.0885, exit_price: 1.0912, profit: 27.0 },
          { id: 2, symbol: "EURUSD", order_type: "SELL", entry_price: 1.0920, exit_price: 1.0895, profit: 25.0 },
          { id: 3, symbol: "EURUSD", order_type: "BUY", entry_price: 1.0875, exit_price: 1.0860, profit: -15.0 },
        ],
      });
    } catch (error) {
      console.error("Backtest failed:", error);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Backtesting</h1>

      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h2 className="text-lg font-semibold text-white mb-4">Configuration</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Symbol</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
            >
              {symbols.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-1">Strategy</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
            >
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-1">Timeframe</label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
            >
              {timeframes.map((tf) => (
                <option key={tf} value={tf}>{tf}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
            />
          </div>
        </div>

        <button
          onClick={handleRunBacktest}
          disabled={isRunning}
          className="mt-4 px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-white font-semibold"
        >
          {isRunning ? "Running Backtest..." : "Run Backtest"}
        </button>
      </div>

      {result && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            <MetricCard label="Total Trades" value={result.metrics.total_trades.toString()} />
            <MetricCard label="Win Rate" value={`${result.metrics.win_rate.toFixed(1)}%`} color="blue" />
            <MetricCard label="Net Profit" value={`$${result.metrics.net_profit.toFixed(0)}`} color="green" />
            <MetricCard label="Profit Factor" value={result.metrics.profit_factor.toFixed(2)} />
            <MetricCard label="Max Drawdown" value={`${result.metrics.max_drawdown_pct.toFixed(1)}%`} color="red" />
            <MetricCard label="Sharpe Ratio" value={result.metrics.sharpe_ratio.toFixed(2)} />
            <MetricCard label="Winners" value={result.metrics.winning_trades.toString()} color="green" />
          </div>

          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h2 className="text-lg font-semibold text-white mb-4">Trade History</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-400 border-b border-slate-700">
                    <th className="text-left py-2">#</th>
                    <th className="text-left py-2">Symbol</th>
                    <th className="text-left py-2">Type</th>
                    <th className="text-right py-2">Entry</th>
                    <th className="text-right py-2">Exit</th>
                    <th className="text-right py-2">Profit</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((trade) => (
                    <tr key={trade.id} className="border-b border-slate-700/50">
                      <td className="py-2 text-slate-400">{trade.id}</td>
                      <td className="py-2 text-white">{trade.symbol}</td>
                      <td className={`py-2 ${trade.order_type === "BUY" ? "text-green-500" : "text-red-500"}`}>
                        {trade.order_type}
                      </td>
                      <td className="py-2 text-right text-slate-300">{trade.entry_price.toFixed(5)}</td>
                      <td className="py-2 text-right text-slate-300">{trade.exit_price.toFixed(5)}</td>
                      <td className={`py-2 text-right font-semibold ${trade.profit >= 0 ? "text-green-500" : "text-red-500"}`}>
                        ${trade.profit.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {!result && !isRunning && (
        <div className="bg-slate-800 rounded-lg p-12 border border-slate-700 text-center">
          <p className="text-slate-400">Configure your backtest parameters and click &quot;Run Backtest&quot; to see results.</p>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, color }: { label: string; value: string; color?: string }) {
  const colorClasses: Record<string, string> = {
    green: "text-green-500",
    red: "text-red-500",
    blue: "text-blue-500",
  };

  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <p className="text-sm text-slate-400">{label}</p>
      <p className={`text-xl font-bold ${color ? colorClasses[color] : "text-white"}`}>
        {value}
      </p>
    </div>
  );
}
