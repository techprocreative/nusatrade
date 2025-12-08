"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDashboardStats } from "@/hooks/api";
import { Skeleton } from "@/components/loading/Skeleton";

function formatCurrency(value: number): string {
  const prefix = value >= 0 ? '+' : '';
  return `${prefix}$${Math.abs(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function DashboardPage() {
  const { data: stats, isLoading, error } = useDashboardStats();

  const statsDisplay = [
    { 
      label: "Balance", 
      value: stats ? `$${stats.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : "$0.00", 
      icon: "💰", 
      color: "text-blue-500" 
    },
    { 
      label: "Equity", 
      value: stats ? `$${stats.equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : "$0.00", 
      icon: "📊", 
      color: "text-green-500" 
    },
    { 
      label: "Open Positions", 
      value: stats ? stats.open_positions.toString() : "0", 
      icon: "📈", 
      color: "text-orange-500" 
    },
    { 
      label: "Today's P/L", 
      value: stats ? formatCurrency(stats.today_pnl) : "$0.00", 
      icon: "💵", 
      color: stats && stats.today_pnl >= 0 ? "text-emerald-500" : "text-red-500" 
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Welcome back! Here&apos;s an overview of your trading activity.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statsDisplay.map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.label}
              </CardTitle>
              <span className="text-2xl">{stat.icon}</span>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <div className={`text-2xl font-bold ${stat.color}`}>
                  {stat.value}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Additional Stats Row */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total P/L</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-xl font-bold ${stats.total_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {formatCurrency(stats.total_pnl)}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Win Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-xl font-bold text-blue-500">
                {stats.win_rate}%
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Trades</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-xl font-bold">
                {stats.total_trades}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4 hover:bg-accent cursor-pointer transition-colors">
            <div className="text-center">
              <span className="text-3xl mb-2 block">💹</span>
              <h3 className="font-semibold">Start Trading</h3>
              <p className="text-sm text-muted-foreground">Open new positions</p>
            </div>
          </Card>
          <Card className="p-4 hover:bg-accent cursor-pointer transition-colors">
            <div className="text-center">
              <span className="text-3xl mb-2 block">🤖</span>
              <h3 className="font-semibold">ML Bots</h3>
              <p className="text-sm text-muted-foreground">Manage trading bots</p>
            </div>
          </Card>
          <Card className="p-4 hover:bg-accent cursor-pointer transition-colors">
            <div className="text-center">
              <span className="text-3xl mb-2 block">📈</span>
              <h3 className="font-semibold">Backtest</h3>
              <p className="text-sm text-muted-foreground">Test strategies</p>
            </div>
          </Card>
        </CardContent>
      </Card>

      {/* Status Notice */}
      <Card className="border-orange-500/50 bg-orange-500/10">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2">
            <span className="text-orange-500">⚠️</span>
            <p className="text-sm">
              <span className="font-semibold">Demo Mode:</span> This platform is currently in development. 
              All trading data is simulated for testing purposes.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
