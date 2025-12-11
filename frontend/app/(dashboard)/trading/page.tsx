"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { usePositions, useTrades, usePlaceOrder, useClosePosition } from "@/hooks/api";
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
import { TableSkeleton } from "@/components/loading/Skeleton";
import { RiskManagementPanel } from "@/components/trading/RiskManagementPanel";
import type { TrailingStopSettings } from "@/types";

const TradingViewChart = dynamic(
  () => import("@/components/charts/TradingViewChart"),
  { ssr: false, loading: () => <div className="h-[400px] bg-muted animate-pulse rounded-lg" /> }
);

const SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD"];

export default function TradingPage() {
  const [symbol, setSymbol] = useState("EURUSD");
  const [orderType, setOrderType] = useState<"BUY" | "SELL">("BUY");
  const [lotSize, setLotSize] = useState("0.1");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [trailingStop, setTrailingStop] = useState<TrailingStopSettings | null>(null);

  const { data: positions = [], isLoading: loadingPositions } = usePositions();
  const { data: trades = [], isLoading: loadingTrades } = useTrades();
  const placeOrderMutation = usePlaceOrder();
  const closePositionMutation = useClosePosition();

  const handleSubmitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    await placeOrderMutation.mutateAsync({
      symbol,
      order_type: orderType,
      lot_size: parseFloat(lotSize),
      price: currentPrice || 1.0,
      stop_loss: stopLoss ? parseFloat(stopLoss) : undefined,
      take_profit: takeProfit ? parseFloat(takeProfit) : undefined,
      trailing_stop: trailingStop || undefined,
    });
    setLotSize("0.1");
    setStopLoss("");
    setTakeProfit("");
  };

  const handleSLTPCalculated = (sl: number, tp: number) => {
    setStopLoss(sl.toFixed(5));
    setTakeProfit(tp.toFixed(5));
  };

  const handleClosePosition = async (positionId: string) => {
    await closePositionMutation.mutateAsync({
      orderId: positionId,
      closePrice: currentPrice || 1.0,
    });
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Trading</h1>
        <Select value={symbol} onValueChange={setSymbol}>
          <SelectTrigger className="w-full sm:w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SYMBOLS.map((s) => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 order-2 lg:order-1">
          <TradingViewChart symbol={symbol} onCrosshairMove={setCurrentPrice} />
        </div>

        <Card className="order-1 lg:order-2">
          <CardHeader>
            <CardTitle>New Order</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmitOrder} className="space-y-4">
              <div className="grid grid-cols-2 gap-2">
                <Button type="button" onClick={() => setOrderType("BUY")} variant={orderType === "BUY" ? "default" : "outline"} className={orderType === "BUY" ? "bg-green-600 hover:bg-green-700" : ""}>BUY</Button>
                <Button type="button" onClick={() => setOrderType("SELL")} variant={orderType === "SELL" ? "default" : "outline"} className={orderType === "SELL" ? "bg-red-600 hover:bg-red-700" : ""}>SELL</Button>
              </div>
              <div className="space-y-2">
                <Label htmlFor="lotSize">Lot Size</Label>
                <Input id="lotSize" type="number" step="0.01" min="0.01" max="10" value={lotSize} onChange={(e) => setLotSize(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="stopLoss">Stop Loss (optional)</Label>
                <Input id="stopLoss" type="number" step="0.00001" value={stopLoss} onChange={(e) => setStopLoss(e.target.value)} placeholder="0.00000" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="takeProfit">Take Profit (optional)</Label>
                <Input id="takeProfit" type="number" step="0.00001" value={takeProfit} onChange={(e) => setTakeProfit(e.target.value)} placeholder="0.00000" />
              </div>

              {/* Risk Management Panel */}
              <RiskManagementPanel
                symbol={symbol}
                orderType={orderType}
                entryPrice={currentPrice}
                onSLTPCalculated={handleSLTPCalculated}
                onTrailingStopChange={setTrailingStop}
              />

              {/* Trailing Stop Indicator */}
              {trailingStop?.enabled && (
                <div className="text-xs p-2 bg-blue-500/10 rounded border border-blue-500/20">
                  <span className="text-blue-400">Trailing Stop Active:</span>
                  <span className="ml-1">Activate at {trailingStop.activation_pips} pips, trail {trailingStop.trail_distance_pips} pips</span>
                </div>
              )}

              <Button type="submit" className="w-full" disabled={placeOrderMutation.isPending} variant={orderType === "BUY" ? "default" : "destructive"}>
                {placeOrderMutation.isPending ? "Placing..." : `${orderType} ${symbol}`}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Open Positions ({positions.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingPositions ? (
            <TableSkeleton rows={3} />
          ) : positions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No open positions</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-muted-foreground border-b">
                    <th className="text-left py-2 px-2">Symbol</th>
                    <th className="text-left py-2 px-2">Type</th>
                    <th className="text-right py-2 px-2">Lots</th>
                    <th className="text-right py-2 px-2">Open</th>
                    <th className="text-right py-2 px-2">Current</th>
                    <th className="text-right py-2 px-2">Profit</th>
                    <th className="text-right py-2 px-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((pos) => (
                    <tr key={pos.id} className="border-b border-border/50">
                      <td className="py-3 px-2">{pos.symbol}</td>
                      <td className={`px-2 ${pos.trade_type === "BUY" ? "text-green-500" : "text-red-500"}`}>{pos.trade_type}</td>
                      <td className="text-right px-2">{pos.lot_size}</td>
                      <td className="text-right text-muted-foreground px-2">{pos.open_price.toFixed(5)}</td>
                      <td className="text-right text-muted-foreground px-2">{pos.current_price?.toFixed(5) || "-"}</td>
                      <td className={`text-right font-semibold px-2 ${(pos.profit ?? 0) >= 0 ? "text-green-500" : "text-red-500"}`}>${(pos.profit ?? 0).toFixed(2)}</td>
                      <td className="text-right px-2">
                        <Button size="sm" variant="destructive" onClick={() => handleClosePosition(pos.id)} disabled={closePositionMutation.isPending}>Close</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
        </CardHeader>
        <CardContent>
          {loadingTrades ? (
            <TableSkeleton rows={5} />
          ) : trades.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No trades yet</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-muted-foreground border-b">
                    <th className="text-left py-2 px-2">Symbol</th>
                    <th className="text-left py-2 px-2">Type</th>
                    <th className="text-right py-2 px-2">Lots</th>
                    <th className="text-right py-2 px-2">Open</th>
                    <th className="text-right py-2 px-2">Close</th>
                    <th className="text-right py-2 px-2">Profit</th>
                    <th className="text-right py-2 px-2 hidden sm:table-cell">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.slice(0, 10).map((trade) => (
                    <tr key={trade.id} className="border-b border-border/50">
                      <td className="py-3 px-2">{trade.symbol}</td>
                      <td className={`px-2 ${trade.trade_type === "BUY" ? "text-green-500" : "text-red-500"}`}>{trade.trade_type}</td>
                      <td className="text-right px-2">{trade.lot_size ?? "-"}</td>
                      <td className="text-right text-muted-foreground px-2">{trade.open_price?.toFixed(5) ?? "-"}</td>
                      <td className="text-right text-muted-foreground px-2">{trade.close_price?.toFixed(5) ?? "-"}</td>
                      <td className={`text-right font-semibold px-2 ${(trade.profit ?? 0) >= 0 ? "text-green-500" : "text-red-500"}`}>${trade.profit?.toFixed(2) ?? "0.00"}</td>
                      <td className="text-right text-muted-foreground text-xs px-2 hidden sm:table-cell">{trade.close_time ? new Date(trade.close_time).toLocaleString() : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
