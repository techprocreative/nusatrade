'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle2, XCircle, Settings, Database, Mail, Gauge, TrendingUp, HardDrive } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Setting {
  key: string;
  value: string;
  category: string;
  is_encrypted: boolean;
  description: string;
  updated_at: string;
  updated_by: string;
}

interface TestResult {
  success: boolean;
  message: string;
  details?: any;
}

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<Record<string, Setting>>({});
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const { toast } = useToast();

  // Form state for each category
  const [aiProvider, setAiProvider] = useState({
    llm_api_key: '',
    llm_base_url: '',
    llm_model: 'gpt-4-turbo-preview',
  });

  const [redis, setRedis] = useState({
    redis_url: '',
  });

  const [email, setEmail] = useState({
    email_provider: 'sendgrid',
    sendgrid_api_key: '',
    email_from: '',
  });

  const [rateLimiting, setRateLimiting] = useState({
    rate_limit_requests: '100',
    rate_limit_window_seconds: '60',
  });

  const [trading, setTrading] = useState({
    max_lot_size: '10.0',
    max_positions_per_user: '20',
    default_slippage_pips: '2.0',
  });

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async (category?: string) => {
    setLoading(true);
    try {
      const url = category
        ? `${API_BASE_URL}/api/v1/admin/settings?category=${category}`
        : `${API_BASE_URL}/api/v1/admin/settings`;

      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) throw new Error('Failed to load settings');

      const data = await response.json();

      // Convert array to object keyed by setting key
      const settingsObj = data.reduce((acc: any, setting: Setting) => {
        acc[setting.key] = setting;
        return acc;
      }, {});

      setSettings(settingsObj);

      // Populate form state (non-encrypted values only)
      data.forEach((setting: Setting) => {
        if (!setting.is_encrypted && setting.value) {
          if (setting.category === 'ai_provider') {
            setAiProvider(prev => ({ ...prev, [setting.key]: setting.value }));
          } else if (setting.category === 'redis') {
            setRedis(prev => ({ ...prev, [setting.key]: setting.value }));
          } else if (setting.category === 'email') {
            setEmail(prev => ({ ...prev, [setting.key]: setting.value }));
          } else if (setting.category === 'rate_limiting') {
            setRateLimiting(prev => ({ ...prev, [setting.key]: setting.value }));
          } else if (setting.category === 'trading') {
            setTrading(prev => ({ ...prev, [setting.key]: setting.value }));
          }
        }
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load settings',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = async (key: string, value: string, category: string, isEncrypted: boolean = false) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/settings/${key}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          value,
          category,
          is_encrypted: isEncrypted,
          description: `${key} configuration`,
        }),
      });

      if (!response.ok) throw new Error('Failed to update setting');

      toast({
        title: 'Success',
        description: `${key} updated successfully`,
      });

      // Reload settings
      await loadSettings();
    } catch (error) {
      toast({
        title: 'Error',
        description: `Failed to update ${key}`,
        variant: 'destructive',
      });
    }
  };

  const testConnection = async (type: 'llm' | 'redis') => {
    setTesting(type);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/test-${type}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      const result = await response.json();
      setTestResults(prev => ({ ...prev, [type]: result }));

      toast({
        title: result.success ? 'Success' : 'Failed',
        description: result.message,
        variant: result.success ? 'default' : 'destructive',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: `Failed to test ${type} connection`,
        variant: 'destructive',
      });
    } finally {
      setTesting(null);
    }
  };

  const saveAIProvider = async () => {
    setLoading(true);
    try {
      if (aiProvider.llm_api_key) {
        await updateSetting('llm_api_key', aiProvider.llm_api_key, 'ai_provider', true);
      }
      if (aiProvider.llm_base_url) {
        await updateSetting('llm_base_url', aiProvider.llm_base_url, 'ai_provider', false);
      }
      if (aiProvider.llm_model) {
        await updateSetting('llm_model', aiProvider.llm_model, 'ai_provider', false);
      }
    } finally {
      setLoading(false);
    }
  };

  const saveRedis = async () => {
    setLoading(true);
    try {
      if (redis.redis_url) {
        await updateSetting('redis_url', redis.redis_url, 'redis', true);
      }
    } finally {
      setLoading(false);
    }
  };

  const saveEmail = async () => {
    setLoading(true);
    try {
      if (email.email_provider) {
        await updateSetting('email_provider', email.email_provider, 'email', false);
      }
      if (email.sendgrid_api_key) {
        await updateSetting('sendgrid_api_key', email.sendgrid_api_key, 'email', true);
      }
      if (email.email_from) {
        await updateSetting('email_from', email.email_from, 'email', false);
      }
    } finally {
      setLoading(false);
    }
  };

  const saveRateLimiting = async () => {
    setLoading(true);
    try {
      await updateSetting('rate_limit_requests', rateLimiting.rate_limit_requests, 'rate_limiting', false);
      await updateSetting('rate_limit_window_seconds', rateLimiting.rate_limit_window_seconds, 'rate_limiting', false);
    } finally {
      setLoading(false);
    }
  };

  const saveTrading = async () => {
    setLoading(true);
    try {
      await updateSetting('max_lot_size', trading.max_lot_size, 'trading', false);
      await updateSetting('max_positions_per_user', trading.max_positions_per_user, 'trading', false);
      await updateSetting('default_slippage_pips', trading.default_slippage_pips, 'trading', false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Settings className="h-8 w-8" />
          System Settings
        </h1>
        <p className="text-muted-foreground mt-2">
          Configure system settings without redeployment. Changes take effect immediately.
        </p>
      </div>

      <Tabs defaultValue="ai" className="space-y-6">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="ai" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            AI Provider
          </TabsTrigger>
          <TabsTrigger value="redis" className="flex items-center gap-2">
            <Database className="h-4 w-4" />
            Redis
          </TabsTrigger>
          <TabsTrigger value="email" className="flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Email
          </TabsTrigger>
          <TabsTrigger value="rate" className="flex items-center gap-2">
            <Gauge className="h-4 w-4" />
            Rate Limit
          </TabsTrigger>
          <TabsTrigger value="trading" className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Trading
          </TabsTrigger>
          <TabsTrigger value="storage" className="flex items-center gap-2">
            <HardDrive className="h-4 w-4" />
            Storage
          </TabsTrigger>
        </TabsList>

        {/* AI Provider Tab */}
        <TabsContent value="ai">
          <Card>
            <CardHeader>
              <CardTitle>AI Provider Configuration</CardTitle>
              <CardDescription>
                Configure LLM provider for AI features. Supports OpenAI-compatible APIs.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="llm_api_key">API Key *</Label>
                <Input
                  id="llm_api_key"
                  type="password"
                  placeholder="sk-..."
                  value={aiProvider.llm_api_key}
                  onChange={(e) => setAiProvider({ ...aiProvider, llm_api_key: e.target.value })}
                />
                <p className="text-sm text-muted-foreground">
                  API key for your LLM provider (encrypted in database)
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="llm_base_url">Base URL (Optional)</Label>
                <Input
                  id="llm_base_url"
                  placeholder="https://api.openai.com/v1"
                  value={aiProvider.llm_base_url}
                  onChange={(e) => setAiProvider({ ...aiProvider, llm_base_url: e.target.value })}
                />
                <p className="text-sm text-muted-foreground">
                  Leave empty for OpenAI, or use:
                  <br />• OpenRouter: https://openrouter.ai/api/v1
                  <br />• Groq: https://api.groq.com/openai/v1
                  <br />• Together AI: https://api.together.xyz/v1
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="llm_model">Model</Label>
                <Input
                  id="llm_model"
                  placeholder="gpt-4-turbo-preview"
                  value={aiProvider.llm_model}
                  onChange={(e) => setAiProvider({ ...aiProvider, llm_model: e.target.value })}
                />
              </div>

              {testResults.llm && (
                <Alert variant={testResults.llm.success ? 'default' : 'destructive'}>
                  {testResults.llm.success ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                  <AlertDescription>
                    {testResults.llm.message}
                    {testResults.llm.details && (
                      <div className="mt-2 text-sm">
                        Provider: {testResults.llm.details.provider} |
                        Model: {testResults.llm.details.model} |
                        Response: {testResults.llm.details.response_time_ms}ms
                      </div>
                    )}
                  </AlertDescription>
                </Alert>
              )}

              <div className="flex gap-2 pt-4">
                <Button onClick={saveAIProvider} disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Save Changes
                </Button>
                <Button
                  variant="outline"
                  onClick={() => testConnection('llm')}
                  disabled={testing === 'llm'}
                >
                  {testing === 'llm' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Test Connection
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Redis Tab */}
        <TabsContent value="redis">
          <Card>
            <CardHeader>
              <CardTitle>Redis Configuration</CardTitle>
              <CardDescription>
                Configure Redis for caching and session management.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="redis_url">Redis URL *</Label>
                <Input
                  id="redis_url"
                  type="password"
                  placeholder="redis://default:password@host:6379"
                  value={redis.redis_url}
                  onChange={(e) => setRedis({ ...redis, redis_url: e.target.value })}
                />
                <p className="text-sm text-muted-foreground">
                  Redis connection string (encrypted in database)
                </p>
              </div>

              {testResults.redis && (
                <Alert variant={testResults.redis.success ? 'default' : 'destructive'}>
                  {testResults.redis.success ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                  <AlertDescription>{testResults.redis.message}</AlertDescription>
                </Alert>
              )}

              <div className="flex gap-2 pt-4">
                <Button onClick={saveRedis} disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Save Changes
                </Button>
                <Button
                  variant="outline"
                  onClick={() => testConnection('redis')}
                  disabled={testing === 'redis'}
                >
                  {testing === 'redis' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Test Connection
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Email Tab */}
        <TabsContent value="email">
          <Card>
            <CardHeader>
              <CardTitle>Email Configuration</CardTitle>
              <CardDescription>
                Configure email service for notifications and alerts.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email_provider">Provider</Label>
                <Input
                  id="email_provider"
                  placeholder="sendgrid"
                  value={email.email_provider}
                  onChange={(e) => setEmail({ ...email, email_provider: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="sendgrid_api_key">SendGrid API Key</Label>
                <Input
                  id="sendgrid_api_key"
                  type="password"
                  placeholder="SG...."
                  value={email.sendgrid_api_key}
                  onChange={(e) => setEmail({ ...email, sendgrid_api_key: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email_from">From Address</Label>
                <Input
                  id="email_from"
                  type="email"
                  placeholder="noreply@example.com"
                  value={email.email_from}
                  onChange={(e) => setEmail({ ...email, email_from: e.target.value })}
                />
              </div>

              <div className="flex gap-2 pt-4">
                <Button onClick={saveEmail} disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Save Changes
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Rate Limiting Tab */}
        <TabsContent value="rate">
          <Card>
            <CardHeader>
              <CardTitle>Rate Limiting</CardTitle>
              <CardDescription>
                Configure API rate limits to prevent abuse.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="rate_limit_requests">Max Requests</Label>
                <Input
                  id="rate_limit_requests"
                  type="number"
                  value={rateLimiting.rate_limit_requests}
                  onChange={(e) => setRateLimiting({ ...rateLimiting, rate_limit_requests: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="rate_limit_window_seconds">Window (seconds)</Label>
                <Input
                  id="rate_limit_window_seconds"
                  type="number"
                  value={rateLimiting.rate_limit_window_seconds}
                  onChange={(e) => setRateLimiting({ ...rateLimiting, rate_limit_window_seconds: e.target.value })}
                />
              </div>

              <div className="flex gap-2 pt-4">
                <Button onClick={saveRateLimiting} disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Save Changes
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trading Tab */}
        <TabsContent value="trading">
          <Card>
            <CardHeader>
              <CardTitle>Trading Parameters</CardTitle>
              <CardDescription>
                Configure trading limits and defaults.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="max_lot_size">Max Lot Size</Label>
                <Input
                  id="max_lot_size"
                  type="number"
                  step="0.01"
                  value={trading.max_lot_size}
                  onChange={(e) => setTrading({ ...trading, max_lot_size: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="max_positions_per_user">Max Positions Per User</Label>
                <Input
                  id="max_positions_per_user"
                  type="number"
                  value={trading.max_positions_per_user}
                  onChange={(e) => setTrading({ ...trading, max_positions_per_user: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="default_slippage_pips">Default Slippage (pips)</Label>
                <Input
                  id="default_slippage_pips"
                  type="number"
                  step="0.1"
                  value={trading.default_slippage_pips}
                  onChange={(e) => setTrading({ ...trading, default_slippage_pips: e.target.value })}
                />
              </div>

              <div className="flex gap-2 pt-4">
                <Button onClick={saveTrading} disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Save Changes
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Storage Tab */}
        <TabsContent value="storage">
          <Card>
            <CardHeader>
              <CardTitle>Storage Configuration</CardTitle>
              <CardDescription>
                Configure Cloudflare R2 for file storage (Coming Soon).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">Storage configuration will be available in the next update.</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
