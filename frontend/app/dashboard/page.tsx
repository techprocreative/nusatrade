"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDashboardStats } from "@/hooks/api";
import { Skeleton } from "@/components/loading/Skeleton";
import { ActiveBotsCard } from "@/components/dashboard/ActiveBotsCard";
import {
  Wallet,
  TrendingUp,
  BarChart3,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  LineChart,
  Bot,
  TestTube2,
  Zap,
  Activity,
  AlertTriangle
} from "lucide-react";

function formatCurrency(value: number): string {
  const prefix = value >= 0 ? '+' : '';
  return `${prefix}$${Math.abs(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function StatCard({
  label,
  value,
  icon: Icon,
  iconColor,
  trend,
  trendValue,
  isLoading
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  iconColor: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  isLoading?: boolean;
}) {
  return (
    <Card className="bg-slate-800/50 border-slate-700/50 hover:border-slate-600 transition-all">
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm text-slate-400 font-medium">{label}</p>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <p className="text-2xl font-bold text-white">{value}</p>
            )}
            {trendValue && (
              <div className={`flex items-center gap-1 text-xs ${trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-slate-400'
                }`}>
                {trend === 'up' ? <ArrowUpRight className="w-3 h-3" /> :
                  trend === 'down' ? <ArrowDownRight className="w-3 h-3" /> : null}
                {trendValue}
              </div>
            )}
          </div>
          <div className={`p-3 rounded-xl ${iconColor}`}>
            <Icon className="w-5 h-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function QuickActionCard({
  href,
  icon: Icon,
  title,
  description,
  gradient
}: {
  href: string;
  icon: React.ElementType;
  title: string;
  description: string;
  gradient: string;
}) {
  return (
    <Link href={href}>
      <Card className="bg-slate-800/50 border-slate-700/50 hover:border-slate-500 hover:bg-slate-800 transition-all cursor-pointer group h-full">
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className={`p-3 rounded-xl ${gradient} group-hover:scale-110 transition-transform`}>
              <Icon className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-white group-hover:text-blue-400 transition-colors">
                {title}
              </h3>
              <p className="text-sm text-slate-400 mt-1">{description}</p>
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 transition-colors" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function DashboardPage() {
  const { data: stats, isLoading, error } = useDashboardStats();

  return (
    <div className="space-y-8 p-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 mt-1">
            Welcome back! Here&apos;s an overview of your trading activity.
          </p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-full">
          <Activity className="w-4 h-4 text-emerald-400" />
          <span className="text-emerald-400 text-sm font-medium">Live</span>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Balance"
          value={stats ? `$${stats.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : "$0.00"}
          icon={Wallet}
          iconColor="bg-blue-500/20 text-blue-400"
          isLoading={isLoading}
        />
        <StatCard
          label="Equity"
          value={stats ? `$${stats.equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : "$0.00"}
          icon={TrendingUp}
          iconColor="bg-emerald-500/20 text-emerald-400"
          isLoading={isLoading}
        />
        <StatCard
          label="Open Positions"
          value={stats ? stats.open_positions.toString() : "0"}
          icon={BarChart3}
          iconColor="bg-orange-500/20 text-orange-400"
          trend="neutral"
          trendValue="Active trades"
          isLoading={isLoading}
        />
        <StatCard
          label="Today's P/L"
          value={stats ? formatCurrency(stats.today_pnl) : "$0.00"}
          icon={DollarSign}
          iconColor={stats && stats.today_pnl >= 0 ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}
          trend={stats ? (stats.today_pnl >= 0 ? 'up' : 'down') : 'neutral'}
          trendValue={stats ? `${stats.today_pnl >= 0 ? '+' : ''}${((stats.today_pnl / (stats.balance || 1)) * 100).toFixed(2)}%` : '0%'}
          isLoading={isLoading}
        />
      </div>

      {/* Secondary Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-slate-800/50 border-slate-700/50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">Total P/L</p>
                  <p className={`text-2xl font-bold ${stats.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {formatCurrency(stats.total_pnl)}
                  </p>
                </div>
                <div className={`w-12 h-12 rounded-full flex items-center justify-center ${stats.total_pnl >= 0 ? 'bg-emerald-500/20' : 'bg-red-500/20'
                  }`}>
                  {stats.total_pnl >= 0 ?
                    <ArrowUpRight className="w-6 h-6 text-emerald-400" /> :
                    <ArrowDownRight className="w-6 h-6 text-red-400" />
                  }
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700/50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">Win Rate</p>
                  <p className="text-2xl font-bold text-blue-400">{stats.win_rate}%</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-blue-400" />
                </div>
              </div>
              <div className="mt-3 h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full"
                  style={{ width: `${stats.win_rate}%` }}
                />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700/50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-400">Total Trades</p>
                  <p className="text-2xl font-bold text-white">{stats.total_trades}</p>
                </div>
                <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center">
                  <Activity className="w-6 h-6 text-purple-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Active ML Bots */}
      <ActiveBotsCard />

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <QuickActionCard
            href="/trading"
            icon={LineChart}
            title="Start Trading"
            description="Open new positions with live charts"
            gradient="bg-gradient-to-br from-blue-500 to-blue-600"
          />
          <QuickActionCard
            href="/bots"
            icon={Bot}
            title="ML Bots"
            description="Manage and train trading bots"
            gradient="bg-gradient-to-br from-emerald-500 to-emerald-600"
          />
          <QuickActionCard
            href="/backtest"
            icon={TestTube2}
            title="Backtesting"
            description="Test strategies on historical data"
            gradient="bg-gradient-to-br from-purple-500 to-purple-600"
          />
        </div>
      </div>

      {/* Demo Mode Notice */}
      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-amber-500/20 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h4 className="font-semibold text-amber-400">Demo Mode Active</h4>
              <p className="text-sm text-slate-400 mt-1">
                This platform is currently in development. All trading data is simulated for testing purposes.
                Connect your MT5 account to start live trading.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
