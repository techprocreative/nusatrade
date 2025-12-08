"use client";

import { useState } from "react";

interface Settings {
  // Trading Settings
  defaultLotSize: string;
  maxLotSize: string;
  maxOpenPositions: string;
  defaultStopLoss: string;
  defaultTakeProfit: string;
  riskPerTrade: string;

  // Notifications
  emailNotifications: boolean;
  tradeAlerts: boolean;
  dailySummary: boolean;

  // API Keys
  openaiKey: string;
  anthropicKey: string;

  // Display
  theme: string;
  timezone: string;
  language: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({
    defaultLotSize: "0.1",
    maxLotSize: "1.0",
    maxOpenPositions: "5",
    defaultStopLoss: "50",
    defaultTakeProfit: "100",
    riskPerTrade: "2",
    emailNotifications: true,
    tradeAlerts: true,
    dailySummary: false,
    openaiKey: "",
    anthropicKey: "",
    theme: "dark",
    timezone: "Asia/Jakarta",
    language: "en",
  });

  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("trading");

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Save settings to backend
      const apiClient = (await import('@/lib/api-client')).default;
      await apiClient.put('/api/v1/users/settings', settings);
      
      // Show success toast
      const { toast } = await import('@/hooks/use-toast');
      toast({
        title: "Settings Saved",
        description: "Your preferences have been updated successfully",
      });
    } catch (error: any) {
      console.error("Failed to save settings:", error);
      const { toast } = await import('@/hooks/use-toast');
      toast({
        variant: "destructive",
        title: "Save Failed",
        description: error.response?.data?.detail || "Failed to save settings",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const tabs = [
    { id: "trading", label: "Trading", icon: "📈" },
    { id: "notifications", label: "Notifications", icon: "🔔" },
    { id: "api", label: "API Keys", icon: "🔑" },
    { id: "display", label: "Display", icon: "🎨" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-slate-400 mt-1">Configure your trading preferences and account settings</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-48 space-y-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg text-left ${activeTab === tab.id
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
                }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 bg-slate-800 rounded-lg border border-slate-700 p-6">
          {activeTab === "trading" && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-white">Trading Settings</h2>

              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Default Lot Size</label>
                  <input
                    type="number"
                    step="0.01"
                    value={settings.defaultLotSize}
                    onChange={(e) => setSettings({ ...settings, defaultLotSize: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                  <p className="text-xs text-slate-500 mt-1">Used as default for new orders</p>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Max Lot Size</label>
                  <input
                    type="number"
                    step="0.1"
                    value={settings.maxLotSize}
                    onChange={(e) => setSettings({ ...settings, maxLotSize: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                  <p className="text-xs text-slate-500 mt-1">Maximum allowed per trade</p>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Max Open Positions</label>
                  <input
                    type="number"
                    value={settings.maxOpenPositions}
                    onChange={(e) => setSettings({ ...settings, maxOpenPositions: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Risk Per Trade (%)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={settings.riskPerTrade}
                    onChange={(e) => setSettings({ ...settings, riskPerTrade: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                  <p className="text-xs text-slate-500 mt-1">Percentage of balance per trade</p>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Default Stop Loss (pips)</label>
                  <input
                    type="number"
                    value={settings.defaultStopLoss}
                    onChange={(e) => setSettings({ ...settings, defaultStopLoss: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Default Take Profit (pips)</label>
                  <input
                    type="number"
                    value={settings.defaultTakeProfit}
                    onChange={(e) => setSettings({ ...settings, defaultTakeProfit: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-white">Notification Settings</h2>

              <div className="space-y-4">
                <label className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg cursor-pointer">
                  <div>
                    <p className="text-white font-medium">Email Notifications</p>
                    <p className="text-sm text-slate-400">Receive important updates via email</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.emailNotifications}
                    onChange={(e) => setSettings({ ...settings, emailNotifications: e.target.checked })}
                    className="w-5 h-5 rounded bg-slate-600 border-slate-500"
                  />
                </label>

                <label className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg cursor-pointer">
                  <div>
                    <p className="text-white font-medium">Trade Alerts</p>
                    <p className="text-sm text-slate-400">Get notified when trades open/close</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.tradeAlerts}
                    onChange={(e) => setSettings({ ...settings, tradeAlerts: e.target.checked })}
                    className="w-5 h-5 rounded bg-slate-600 border-slate-500"
                  />
                </label>

                <label className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg cursor-pointer">
                  <div>
                    <p className="text-white font-medium">Daily Summary</p>
                    <p className="text-sm text-slate-400">Receive daily trading performance report</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.dailySummary}
                    onChange={(e) => setSettings({ ...settings, dailySummary: e.target.checked })}
                    className="w-5 h-5 rounded bg-slate-600 border-slate-500"
                  />
                </label>
              </div>
            </div>
          )}

          {activeTab === "api" && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-white">API Keys</h2>
              <p className="text-slate-400">Configure AI provider API keys for enhanced features</p>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">OpenAI API Key</label>
                  <input
                    type="password"
                    value={settings.openaiKey}
                    onChange={(e) => setSettings({ ...settings, openaiKey: e.target.value })}
                    placeholder="sk-..."
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                  <p className="text-xs text-slate-500 mt-1">Used for AI Supervisor chat</p>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Anthropic API Key</label>
                  <input
                    type="password"
                    value={settings.anthropicKey}
                    onChange={(e) => setSettings({ ...settings, anthropicKey: e.target.value })}
                    placeholder="sk-ant-..."
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  />
                  <p className="text-xs text-slate-500 mt-1">Fallback AI provider</p>
                </div>
              </div>

              <div className="p-4 bg-yellow-600/10 border border-yellow-600/30 rounded-lg">
                <p className="text-yellow-400 text-sm">
                  ⚠️ API keys are stored securely. Never share your keys with anyone.
                </p>
              </div>
            </div>
          )}

          {activeTab === "display" && (
            <div className="space-y-6">
              <h2 className="text-lg font-semibold text-white">Display Settings</h2>

              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Theme</label>
                  <select
                    value={settings.theme}
                    onChange={(e) => setSettings({ ...settings, theme: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  >
                    <option value="dark">Dark</option>
                    <option value="light">Light</option>
                    <option value="system">System</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Timezone</label>
                  <select
                    value={settings.timezone}
                    onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  >
                    <option value="Asia/Jakarta">Asia/Jakarta (GMT+7)</option>
                    <option value="Asia/Singapore">Asia/Singapore (GMT+8)</option>
                    <option value="Europe/London">Europe/London (GMT+0)</option>
                    <option value="America/New_York">America/New_York (GMT-5)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Language</label>
                  <select
                    value={settings.language}
                    onChange={(e) => setSettings({ ...settings, language: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  >
                    <option value="en">English</option>
                    <option value="id">Bahasa Indonesia</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Save Button */}
          <div className="mt-8 pt-6 border-t border-slate-700">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-white font-semibold"
            >
              {isSaving ? "Saving..." : "Save Settings"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
