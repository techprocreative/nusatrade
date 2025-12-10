"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUserSettings, useUpdateUserSettings, type UserSettings } from "@/hooks/api/useSettings";
import { Loader2, User, Mail, Calendar } from "lucide-react";

interface Settings extends UserSettings {
  llmApiKey: string;
  llmBaseUrl: string;
  llmModel: string;
}

interface UserProfile {
  email: string;
  full_name: string;
  created_at?: string;
}

export default function SettingsPage() {
  // Fetch settings from database
  const { data: savedSettings, isLoading: loadingSettings } = useUserSettings();
  const updateSettingsMutation = useUpdateUserSettings();

  // User profile state
  const [profile, setProfile] = useState<UserProfile>({
    email: "",
    full_name: "",
    created_at: ""
  });
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileName, setProfileName] = useState("");

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
    llmApiKey: "",
    llmBaseUrl: "",
    llmModel: "gpt-4-turbo-preview",
    theme: "dark",
    timezone: "Asia/Jakarta",
    language: "en",
  });

  // Load settings from database when data is available
  useEffect(() => {
    if (savedSettings) {
      setSettings(prev => ({
        ...prev,
        ...savedSettings,
        // Keep sensitive fields empty if not returned
        llmApiKey: savedSettings.llmApiKey || "",
        llmBaseUrl: savedSettings.llmBaseUrl || "",
        llmModel: savedSettings.llmModel || "gpt-4-turbo-preview",
      }));
    }
  }, [savedSettings]);

  // Fetch user profile
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await fetch("/api/v1/users/me", {
          headers: {
            "Authorization": `Bearer ${localStorage.getItem("access_token")}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setProfile(data);
          setProfileName(data.full_name || "");
        }
      } catch (error) {
        console.error("Failed to fetch profile", error);
      } finally {
        setProfileLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const handleSave = async () => {
    await updateSettingsMutation.mutateAsync(settings);
  };

  // Show loading state while fetching settings
  if (loadingSettings) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        <span className="ml-2 text-slate-400">Loading settings...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Configure your trading preferences and account settings
        </p>
      </div>

      <Tabs defaultValue="trading" className="space-y-6">
        <TabsList className="bg-slate-800 border border-slate-700">
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="trading">Trading</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="api">API Keys</TabsTrigger>
          <TabsTrigger value="display">Display</TabsTrigger>
        </TabsList>

        {/* Profile Settings */}
        <TabsContent value="profile">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>
                Manage your account details
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {profileLoading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-4 p-4 bg-slate-700/50 rounded-lg">
                    <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                      <User className="w-8 h-8 text-white" />
                    </div>
                    <div>
                      <p className="text-lg font-medium text-white">{profile.full_name || "User"}</p>
                      <p className="text-sm text-muted-foreground">{profile.email}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="fullName">Full Name</Label>
                      <Input
                        id="fullName"
                        value={profileName}
                        onChange={(e) => setProfileName(e.target.value)}
                        placeholder="Your name"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="email">Email Address</Label>
                      <div className="flex items-center gap-2">
                        <Mail className="w-4 h-4 text-muted-foreground" />
                        <span className="text-slate-300">{profile.email}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">Email cannot be changed</p>
                    </div>
                  </div>

                  {profile.created_at && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="w-4 h-4" />
                      <span>Member since {new Date(profile.created_at).toLocaleDateString()}</span>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trading Settings */}
        <TabsContent value="trading">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle>Trading Settings</CardTitle>
              <CardDescription>
                Configure default values for your trading operations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="defaultLotSize">Default Lot Size</Label>
                  <Input
                    id="defaultLotSize"
                    type="number"
                    step="0.01"
                    value={settings.defaultLotSize}
                    onChange={(e) =>
                      setSettings({ ...settings, defaultLotSize: e.target.value })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Used as default for new orders
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="maxLotSize">Max Lot Size</Label>
                  <Input
                    id="maxLotSize"
                    type="number"
                    step="0.1"
                    value={settings.maxLotSize}
                    onChange={(e) =>
                      setSettings({ ...settings, maxLotSize: e.target.value })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Maximum allowed per trade
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="maxOpenPositions">Max Open Positions</Label>
                  <Input
                    id="maxOpenPositions"
                    type="number"
                    value={settings.maxOpenPositions}
                    onChange={(e) =>
                      setSettings({ ...settings, maxOpenPositions: e.target.value })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="riskPerTrade">Risk Per Trade (%)</Label>
                  <Input
                    id="riskPerTrade"
                    type="number"
                    step="0.5"
                    value={settings.riskPerTrade}
                    onChange={(e) =>
                      setSettings({ ...settings, riskPerTrade: e.target.value })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Percentage of balance per trade
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="defaultStopLoss">Default Stop Loss (pips)</Label>
                  <Input
                    id="defaultStopLoss"
                    type="number"
                    value={settings.defaultStopLoss}
                    onChange={(e) =>
                      setSettings({ ...settings, defaultStopLoss: e.target.value })
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="defaultTakeProfit">Default Take Profit (pips)</Label>
                  <Input
                    id="defaultTakeProfit"
                    type="number"
                    value={settings.defaultTakeProfit}
                    onChange={(e) =>
                      setSettings({ ...settings, defaultTakeProfit: e.target.value })
                    }
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notification Settings */}
        <TabsContent value="notifications">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle>Notification Settings</CardTitle>
              <CardDescription>
                Configure how and when you receive notifications
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg">
                <div className="space-y-0.5">
                  <Label htmlFor="emailNotifications" className="text-base">
                    Email Notifications
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Receive important updates via email
                  </p>
                </div>
                <Switch
                  id="emailNotifications"
                  checked={settings.emailNotifications}
                  onCheckedChange={(checked) =>
                    setSettings({ ...settings, emailNotifications: checked })
                  }
                />
              </div>

              <div className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg">
                <div className="space-y-0.5">
                  <Label htmlFor="tradeAlerts" className="text-base">
                    Trade Alerts
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Get notified when trades open/close
                  </p>
                </div>
                <Switch
                  id="tradeAlerts"
                  checked={settings.tradeAlerts}
                  onCheckedChange={(checked) =>
                    setSettings({ ...settings, tradeAlerts: checked })
                  }
                />
              </div>

              <div className="flex items-center justify-between p-4 bg-slate-700/50 rounded-lg">
                <div className="space-y-0.5">
                  <Label htmlFor="dailySummary" className="text-base">
                    Daily Summary
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Receive daily trading performance report
                  </p>
                </div>
                <Switch
                  id="dailySummary"
                  checked={settings.dailySummary}
                  onCheckedChange={(checked) =>
                    setSettings({ ...settings, dailySummary: checked })
                  }
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Settings */}
        <TabsContent value="api">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle>AI Provider Configuration</CardTitle>
              <CardDescription>
                Configure OpenAI-compatible API for AI Supervisor and trading analysis
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="llmApiKey">API Key *</Label>
                <Input
                  id="llmApiKey"
                  type="password"
                  value={settings.llmApiKey}
                  onChange={(e) =>
                    setSettings({ ...settings, llmApiKey: e.target.value })
                  }
                  placeholder="sk-..."
                />
                <p className="text-xs text-muted-foreground">
                  Your LLM provider API key (supports OpenAI, OpenRouter, Groq, etc.)
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="llmBaseUrl">Base URL (Optional)</Label>
                <Input
                  id="llmBaseUrl"
                  type="text"
                  value={settings.llmBaseUrl}
                  onChange={(e) =>
                    setSettings({ ...settings, llmBaseUrl: e.target.value })
                  }
                  placeholder="https://api.openai.com/v1"
                />
                <p className="text-xs text-muted-foreground">
                  Leave empty for OpenAI. Common alternatives:
                </p>
                <ul className="text-xs text-muted-foreground ml-4 list-disc">
                  <li>OpenRouter: https://openrouter.ai/api/v1</li>
                  <li>Groq: https://api.groq.com/openai/v1</li>
                  <li>Together AI: https://api.together.xyz/v1</li>
                  <li>DeepSeek: https://api.deepseek.com/v1</li>
                  <li>Local (Ollama): http://localhost:11434/v1</li>
                </ul>
              </div>

              <div className="space-y-2">
                <Label htmlFor="llmModel">Model</Label>
                <Input
                  id="llmModel"
                  type="text"
                  value={settings.llmModel}
                  onChange={(e) =>
                    setSettings({ ...settings, llmModel: e.target.value })
                  }
                  placeholder="gpt-4-turbo-preview"
                />
                <p className="text-xs text-muted-foreground">
                  Examples: gpt-4o, gpt-4-turbo, claude-3-opus, llama-3.1-70b, deepseek-chat
                </p>
              </div>

              <div className="p-4 bg-blue-600/10 border border-blue-600/30 rounded-lg">
                <p className="text-blue-400 text-sm font-medium mb-2">
                  OpenAI Compatible
                </p>
                <p className="text-muted-foreground text-sm">
                  This settings supports any OpenAI-compatible API. You can use
                  providers like OpenRouter, Groq, Together AI, DeepSeek, or even
                  local models via Ollama.
                </p>
              </div>

              <div className="p-4 bg-yellow-600/10 border border-yellow-600/30 rounded-lg">
                <p className="text-yellow-400 text-sm">
                  API keys are stored securely. Never share your keys with anyone.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Display Settings */}
        <TabsContent value="display">
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle>Display Settings</CardTitle>
              <CardDescription>
                Customize the appearance of your dashboard
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="theme">Theme</Label>
                  <Select
                    value={settings.theme}
                    onValueChange={(value) =>
                      setSettings({ ...settings, theme: value })
                    }
                  >
                    <SelectTrigger id="theme">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="dark">Dark</SelectItem>
                      <SelectItem value="light">Light</SelectItem>
                      <SelectItem value="system">System</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timezone">Timezone</Label>
                  <Select
                    value={settings.timezone}
                    onValueChange={(value) =>
                      setSettings({ ...settings, timezone: value })
                    }
                  >
                    <SelectTrigger id="timezone">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Asia/Jakarta">
                        Asia/Jakarta (GMT+7)
                      </SelectItem>
                      <SelectItem value="Asia/Singapore">
                        Asia/Singapore (GMT+8)
                      </SelectItem>
                      <SelectItem value="Europe/London">
                        Europe/London (GMT+0)
                      </SelectItem>
                      <SelectItem value="America/New_York">
                        America/New_York (GMT-5)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="language">Language</Label>
                  <Select
                    value={settings.language}
                    onValueChange={(value) =>
                      setSettings({ ...settings, language: value })
                    }
                  >
                    <SelectTrigger id="language">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="id">Bahasa Indonesia</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={updateSettingsMutation.isPending}>
          {updateSettingsMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            "Save Settings"
          )}
        </Button>
      </div>
    </div>
  );
}
