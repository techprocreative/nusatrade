"use client";

import { useState, useEffect, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useWebSocketConnection, useTradeNotifications } from "@/hooks/useWebSocket";
import { wsClient } from "@/lib/websocket";
import {
  LayoutDashboard,
  LineChart,
  TestTube2,
  Bot,
  Brain,
  Link2,
  Shield,
  Settings,
  LogOut,
  Menu,
  X,
  Wifi,
  WifiOff,
  ChevronRight,
  ShieldCheck,
  Sparkles
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/trading", label: "Trading", icon: LineChart },
  { href: "/strategies", label: "Strategies", icon: Sparkles },
  { href: "/backtest", label: "Backtest", icon: TestTube2 },
  { href: "/bots", label: "ML Bots", icon: Bot },
  { href: "/ai-supervisor", label: "AI Supervisor", icon: Brain },
  { href: "/connections", label: "Connections", icon: Link2 },
  { href: "/security", label: "Security", icon: Shield },
  { href: "/settings", label: "Settings", icon: Settings },
];

const adminNavItems = [
  { href: "/admin/settings", label: "Admin Panel", icon: ShieldCheck },
];

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { isConnected } = useWebSocketConnection();

  // Setup WebSocket connection and notifications
  useTradeNotifications();

  useEffect(() => {
    if (user) {
      const token = localStorage.getItem('token');
      if (token) {
        wsClient.connect(token);
      }
    }

    return () => {
      wsClient.disconnect();
    };
  }, [user]);

  const Sidebar = ({ mobile = false }: { mobile?: boolean }) => (
    <aside
      className={cn(
        "bg-slate-900 border-slate-800",
        mobile
          ? "fixed inset-y-0 left-0 z-50 w-72 border-r transform transition-transform duration-300 ease-in-out lg:hidden"
          : "hidden lg:flex lg:w-72 lg:flex-col lg:border-r",
        mobile && !isMobileMenuOpen && "-translate-x-full"
      )}
    >
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-lg flex items-center justify-center">
              <LineChart className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              NusaTrade
            </span>
          </Link>
          {mobile && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </Button>
          )}
        </div>

        {/* Connection Status */}
        <div className="px-4 py-3 border-b border-slate-800">
          <div className={cn(
            "flex items-center gap-2 px-3 py-2 rounded-lg text-sm",
            isConnected ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
          )}>
            {isConnected ? (
              <>
                <Wifi className="w-4 h-4" />
                <span>Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4" />
                <span>Disconnected</span>
              </>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => mobile && setIsMobileMenuOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group",
                  isActive
                    ? "bg-gradient-to-r from-blue-500/20 to-emerald-500/20 text-white border border-blue-500/30"
                    : "text-slate-400 hover:bg-slate-800 hover:text-white"
                )}
              >
                <Icon className={cn(
                  "w-5 h-5 transition-colors",
                  isActive ? "text-blue-400" : "text-slate-500 group-hover:text-slate-300"
                )} />
                <span className="flex-1">{item.label}</span>
                {isActive && (
                  <ChevronRight className="w-4 h-4 text-blue-400" />
                )}
              </Link>
            );
          })}

          {/* Admin Section - only show for admin users */}
          {user?.role === "admin" && (
            <>
              <div className="pt-4 pb-2">
                <p className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Admin</p>
              </div>
              {adminNavItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => mobile && setIsMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group",
                      isActive
                        ? "bg-gradient-to-r from-amber-500/20 to-red-500/20 text-white border border-amber-500/30"
                        : "text-amber-400/70 hover:bg-slate-800 hover:text-amber-400"
                    )}
                  >
                    <Icon className={cn(
                      "w-5 h-5 transition-colors",
                      isActive ? "text-amber-400" : "text-amber-500/50 group-hover:text-amber-400"
                    )} />
                    <span className="flex-1">{item.label}</span>
                    {isActive && (
                      <ChevronRight className="w-4 h-4 text-amber-400" />
                    )}
                  </Link>
                );
              })}
            </>
          )}
        </nav>

        {/* User Info & Logout */}
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-3 mb-4 p-3 bg-slate-800/50 rounded-lg">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-semibold">
              {user?.full_name?.charAt(0) || user?.email?.charAt(0) || "U"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-white truncate text-sm">
                {user?.full_name || "User"}
              </p>
              <p className="text-xs text-slate-400 truncate">
                {user?.email}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white"
            onClick={logout}
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </div>
    </aside>
  );

  return (
    <ProtectedRoute>
      <div className="flex min-h-screen bg-slate-950">
        {/* Desktop Sidebar */}
        <Sidebar />

        {/* Mobile Sidebar */}
        <Sidebar mobile />

        {/* Mobile Overlay */}
        {isMobileMenuOpen && (
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
          />
        )}

        {/* Main Content */}
        <main className="flex-1 flex flex-col min-w-0">
          {/* Mobile Header */}
          <header className="lg:hidden sticky top-0 z-30 flex items-center gap-4 border-b border-slate-800 bg-slate-900 px-4 py-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileMenuOpen(true)}
              className="text-slate-400 hover:text-white"
            >
              <Menu className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-lg flex items-center justify-center">
                <LineChart className="w-4 h-4 text-white" />
              </div>
              <span className="text-lg font-semibold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
                NusaTrade
              </span>
            </div>
          </header>

          {/* Page Content */}
          <div className="flex-1 overflow-auto bg-slate-950">{children}</div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
