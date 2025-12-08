"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";

// Dynamically import chart to avoid SSR issues
const TradingViewChart = dynamic(
  () => import("@/components/charts/TradingViewChart"),
  { ssr: false, loading: () => <div className="h-[400px] bg-slate-800 animate-pulse rounded-lg" /> }
);

interface Position {
  id: string;
  symbol: string;
  type: "BUY" | "SELL";
  lotSize: number;
  openPrice: number;
  currentPrice: number;
  profit: number;
  openTime: string;
}

interface Trade {
  id: string;
  symbol: string;
  type: string;
  lotSize: number;
  openPrice: number;
  closePrice: number;
  profit: number;
  closeTime: string;
}

export default function TradingPage() {
  const [symbol, setSymbol] = useState("EURUSD");
  const [orderType, setOrderType] = useState<"BUY" | "SELL">("BUY");
  const [lotSize, setLotSize] = useState("0.1");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [positions, setPositions] = useState<Position[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);

  const symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD"];

  // Simulate fetching positions
  useEffect(() => {
    // TODO: Fetch from API
    setPositions([
      {
        id: "1",
        symbol: "EURUSD",
        type: "BUY",
        lotSize: 0.1,
        openPrice: 1.0885,
        currentPrice: 1.0892,
        profit: 7.0,
        openTime: new Date().toISOString(),
      },
    ]);

    setTrades([
      {
        id: "1",
        symbol: "GBPUSD",
        type: "SELL",
        lotSize: 0.05,
        openPrice: 1.265,
        closePrice: 1.262,
        profit: 15.0,
        closeTime: new Date().toISOString(),
      },
    ]);
  }, []);

  const handleSubmitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // TODO: Call API to place order
      console.log("Placing order:", {
        symbol,
        orderType,
        lotSize: parseFloat(lotSize),
        stopLoss: stopLoss ? parseFloat(stopLoss) : null,
        takeProfit: takeProfit ? parseFloat(takeProfit) : null,
      });

      // Simulate success
      await new Promise((r) => setTimeout(r, 500));
      alert(`${orderType} order placed for ${lotSize} lots of ${symbol}`);
    } catch (error) {
      console.error("Order failed:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClosePosition = async (positionId: string) => {
    // TODO: Call API to close position
    setPositions(positions.filter((p) => p.id !== positionId));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Trading</h1>
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {symbols.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {/* Chart and Order Form */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Chart */}
        <div className="lg:col-span-3">
          <TradingViewChart
            symbol={symbol}
            onCrosshairMove={setCurrentPrice}
          />
        </div>

        {/* Order Form */}
        <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">New Order</h2>

          <form onSubmit={handleSubmitOrder} className="space-y-4">
            {/* Order Type Buttons */}
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setOrderType("BUY")}
                className={`py-3 rounded-lg font-semibold transition-colors ${orderType === "BUY"
                    ? "bg-green-600 text-white"
                    : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                  }`}
              >
                BUY
              </button>
              <button
                type="button"
                onClick={() => setOrderType("SELL")}
                className={`py-3 rounded-lg font-semibold transition-colors ${orderType === "SELL"
                    ? "bg-red-600 text-white"
                    : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                  }`}
              >
                SELL
              </button>
            </div>

            {/* Lot Size */}
            <div>
              <label className="block text-sm text-slate-400 mb-1">
                Lot Size
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                max="10"
                value={lotSize}
                onChange={(e) => setLotSize(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Stop Loss */}
            <div>
              <label className="block text-sm text-slate-400 mb-1">
                Stop Loss (optional)
              </label>
              <input
                type="number"
                step="0.00001"
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
                placeholder="0.00000"
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Take Profit */}
            <div>
              <label className="block text-sm text-slate-400 mb-1">
                Take Profit (optional)
              </label>
              <input
                type="number"
                step="0.00001"
                value={takeProfit}
                onChange={(e) => setTakeProfit(e.target.value)}
                placeholder="0.00000"
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className={`w-full py-3 rounded-lg font-semibold text-white transition-colors ${orderType === "BUY"
                  ? "bg-green-600 hover:bg-green-700"
                  : "bg-red-600 hover:bg-red-700"
                } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {isLoading ? "Placing Order..." : `${orderType} ${symbol}`}
            </button>
          </form>
        </div>
      </div>

      {/* Open Positions */}
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <h2 className="text-lg font-semibold text-white mb-4">
          Open Positions ({positions.length})
        </h2>

        {positions.length === 0 ? (
          <p className="text-slate-400 text-center py-4">No open positions</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2">Symbol</th>
                  <th className="text-left py-2">Type</th>
                  <th className="text-right py-2">Lots</th>
                  <th className="text-right py-2">Open Price</th>
                  <th className="text-right py-2">Current</th>
                  <th className="text-right py-2">Profit</th>
                  <th className="text-right py-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => (
                  <tr key={pos.id} className="border-b border-slate-700/50">
                    <td className="py-3 text-white">{pos.symbol}</td>
                    <td className={`py-3 ${pos.type === "BUY" ? "text-green-500" : "text-red-500"}`}>
                      {pos.type}
                    </td>
                    <td className="py-3 text-right text-white">{pos.lotSize}</td>
                    <td className="py-3 text-right text-slate-300">{pos.openPrice.toFixed(5)}</td>
                    <td className="py-3 text-right text-slate-300">{pos.currentPrice.toFixed(5)}</td>
                    <td className={`py-3 text-right font-semibold ${pos.profit >= 0 ? "text-green-500" : "text-red-500"}`}>
                      ${pos.profit.toFixed(2)}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleClosePosition(pos.id)}
                        className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-white text-xs"
                      >
                        Close
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Trade History */}
      <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
        <h2 className="text-lg font-semibold text-white mb-4">Trade History</h2>

        {trades.length === 0 ? (
          <p className="text-slate-400 text-center py-4">No trades yet</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2">Symbol</th>
                  <th className="text-left py-2">Type</th>
                  <th className="text-right py-2">Lots</th>
                  <th className="text-right py-2">Open</th>
                  <th className="text-right py-2">Close</th>
                  <th className="text-right py-2">Profit</th>
                  <th className="text-right py-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => (
                  <tr key={trade.id} className="border-b border-slate-700/50">
                    <td className="py-3 text-white">{trade.symbol}</td>
                    <td className={`py-3 ${trade.type === "BUY" ? "text-green-500" : "text-red-500"}`}>
                      {trade.type}
                    </td>
                    <td className="py-3 text-right text-white">{trade.lotSize}</td>
                    <td className="py-3 text-right text-slate-300">{trade.openPrice.toFixed(5)}</td>
                    <td className="py-3 text-right text-slate-300">{trade.closePrice.toFixed(5)}</td>
                    <td className={`py-3 text-right font-semibold ${trade.profit >= 0 ? "text-green-500" : "text-red-500"}`}>
                      ${trade.profit.toFixed(2)}
                    </td>
                    <td className="py-3 text-right text-slate-400">
                      {new Date(trade.closeTime).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
