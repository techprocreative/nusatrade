"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useWebSocketConnection, useTradeNotifications } from "@/hooks/useWebSocket";
import { connectSocket, disconnectSocket } from "@/lib/websocket";
import { useEffect } from "react";

const navItems = [
  { href: "/dashboard", label: "Overview", icon: "📊" },
  { href: "/dashboard/trading", label: "Trading", icon: "💹" },
  { href: "/dashboard/backtest", label: "Backtest", icon: "📈" },
  { href: "/dashboard/bots", label: "Bots", icon: "🤖" },
  { href: "/dashboard/ai-supervisor", label: "AI Supervisor", icon: "🧠" },
  { href: "/dashboard/connections", label: "Connections", icon: "🔗" },
  { href: "/dashboard/security", label: "Security", icon: "🔐" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
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
      connectSocket();
    }

    return () => {
      disconnectSocket();
    };
  }, [user]);

  const Sidebar = ({ mobile = false }: { mobile?: boolean }) => (
    <aside
      className={cn(
        "bg-card border-border",
        mobile
          ? "fixed inset-y-0 left-0 z-50 w-64 border-r transform transition-transform duration-200 lg:hidden"
          : "hidden lg:flex lg:w-64 lg:flex-col lg:border-r",
        mobile && !isMobileMenuOpen && "-translate-x-full"
      )}
    >
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="p-6 border-b border-border flex items-center justify-between">
          <h1 className="text-xl font-bold">Forex AI</h1>
          {mobile && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              ✕
            </Button>
          )}
        </div>

        {/* Connection Status */}
        <div className="px-4 py-2 border-b border-border">
          <div className="flex items-center gap-2 text-xs">
            <div
              className={cn(
                "w-2 h-2 rounded-full",
                isConnected ? "bg-green-500" : "bg-red-500"
              )}
            />
            <span className="text-muted-foreground">
              {isConnected ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => mobile && setIsMobileMenuOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <span className="text-lg">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Info & Logout */}
        <div className="p-4 border-t border-border">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm flex-1 min-w-0">
              <p className="font-medium truncate">{user?.full_name || "User"}</p>
              <p className="text-xs text-muted-foreground truncate">
                {user?.email}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={logout}
          >
            Logout
          </Button>
        </div>
      </div>
    </aside>
  );

  return (
    <ProtectedRoute>
      <div className="flex min-h-screen">
        {/* Desktop Sidebar */}
        <Sidebar />

        {/* Mobile Sidebar */}
        <Sidebar mobile />

        {/* Mobile Overlay */}
        {isMobileMenuOpen && (
          <div
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
          />
        )}

        {/* Main Content */}
        <main className="flex-1 flex flex-col min-w-0">
          {/* Mobile Header */}
          <header className="lg:hidden sticky top-0 z-30 flex items-center gap-4 border-b bg-card px-4 py-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileMenuOpen(true)}
            >
              ☰
            </Button>
            <h1 className="text-lg font-semibold">Forex AI</h1>
          </header>

          {/* Page Content */}
          <div className="flex-1 p-4 md:p-6 lg:p-8 overflow-auto">{children}</div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
