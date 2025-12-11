"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useActiveBots } from "@/hooks/api";
import { Bot, TrendingUp, TrendingDown, Minus, Zap, ArrowRight } from "lucide-react";

function formatTimeAgo(dateString: string | undefined): string {
  if (!dateString) return "";
  
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

function DirectionIcon({ direction }: { direction: string }) {
  if (direction === "BUY") {
    return <TrendingUp className="w-4 h-4 text-emerald-400" />;
  }
  if (direction === "SELL") {
    return <TrendingDown className="w-4 h-4 text-red-400" />;
  }
  return <Minus className="w-4 h-4 text-slate-400" />;
}

export function ActiveBotsCard() {
  const { data, isLoading } = useActiveBots();

  // Don't show if no active bots
  if (!isLoading && (!data || data.active_count === 0)) {
    return null;
  }

  return (
    <Card className="border-emerald-500/30 bg-emerald-500/5">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-3 text-lg">
            <div className="p-2 bg-emerald-500/20 rounded-lg">
              <Bot className="w-5 h-5 text-emerald-400" />
            </div>
            <span className="text-white">ML Bot Active</span>
            {/* Pulse indicator */}
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
          </CardTitle>
          <Link href="/bots">
            <Button variant="ghost" size="sm" className="text-emerald-400 hover:text-emerald-300">
              View All
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-4">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-400"></div>
          </div>
        ) : (
          <>
            {/* Active Bots List */}
            <div className="space-y-3">
              {data?.bots.map((bot) => (
                <div
                  key={bot.id}
                  className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700/50"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-white">{bot.name}</h4>
                      <Badge variant="outline" className="text-xs">
                        {bot.symbol}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      {bot.model_type.replace("_", " ")} • {bot.timeframe}
                      {bot.accuracy > 0 && ` • ${(bot.accuracy * 100).toFixed(1)}% accuracy`}
                    </p>
                    {bot.last_prediction && (
                      <div className="flex items-center gap-2 mt-2">
                        <DirectionIcon direction={bot.last_prediction.direction} />
                        <span className={`text-xs font-medium ${
                          bot.last_prediction.direction === "BUY" ? "text-emerald-400" :
                          bot.last_prediction.direction === "SELL" ? "text-red-400" :
                          "text-slate-400"
                        }`}>
                          {bot.last_prediction.direction}
                        </span>
                        {bot.last_prediction.entry_price && (
                          <span className="text-xs text-slate-400">
                            @ {bot.last_prediction.entry_price.toFixed(5)}
                          </span>
                        )}
                        <span className="text-xs text-slate-500">
                          ({formatTimeAgo(bot.last_prediction.created_at)})
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
                      <Zap className="w-3 h-3 mr-1" />
                      Running
                    </Badge>
                  </div>
                </div>
              ))}
            </div>

            {/* Today's Stats */}
            {data && data.total_signals_today > 0 && (
              <div className="pt-3 border-t border-slate-700/50">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-400">Today&apos;s Activity</span>
                  <div className="flex items-center gap-4">
                    <div className="text-center">
                      <span className="text-lg font-bold text-white">{data.total_signals_today}</span>
                      <span className="text-xs text-slate-400 ml-1">signals</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
