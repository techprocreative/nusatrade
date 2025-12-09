"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useStrategies } from "@/hooks/api/useStrategies";
import { StrategyBuilder, StrategyPreview, StrategyCard } from "@/components/strategies";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/loading/Skeleton";
import type { AIStrategyResponse, TradingStrategy } from "@/types";
import {
  Sparkles,
  ListFilter,
  Bot,
  Plus,
  FolderOpen,
} from "lucide-react";

export default function StrategiesPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("builder");
  const [generatedResponse, setGeneratedResponse] = useState<AIStrategyResponse | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<TradingStrategy | null>(null);

  const { data: strategies = [], isLoading } = useStrategies();

  const handleGenerated = (response: AIStrategyResponse) => {
    setGeneratedResponse(response);
  };

  const handleSaved = () => {
    setGeneratedResponse(null);
    setActiveTab("library");
  };

  const handleClear = () => {
    setGeneratedResponse(null);
  };

  const handleSelectStrategy = (strategy: TradingStrategy) => {
    setSelectedStrategy(strategy);
  };

  const handleBacktest = (strategy: TradingStrategy) => {
    router.push(`/backtest?strategy=${strategy.id}`);
  };

  const activeStrategies = strategies.filter((s) => s.is_active);
  const aiGeneratedStrategies = strategies.filter((s) => s.strategy_type === 'ai_generated');

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-yellow-500" />
            AI Strategy Builder
          </h1>
          <p className="text-muted-foreground mt-1">
            Create, manage, and backtest your trading strategies with AI
          </p>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 rounded-lg">
            <FolderOpen className="w-4 h-4 text-slate-400" />
            <span className="text-slate-300">{strategies.length} Strategies</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/10 rounded-lg">
            <Bot className="w-4 h-4 text-green-400" />
            <span className="text-green-400">{activeStrategies.length} Active</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-slate-800 border border-slate-700">
          <TabsTrigger value="builder" className="flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            AI Builder
          </TabsTrigger>
          <TabsTrigger value="library" className="flex items-center gap-2">
            <ListFilter className="w-4 h-4" />
            My Strategies ({strategies.length})
          </TabsTrigger>
        </TabsList>

        {/* AI Builder Tab */}
        <TabsContent value="builder" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Builder Form */}
            <div>
              <StrategyBuilder onGenerated={handleGenerated} />
            </div>

            {/* Right: Preview */}
            <div>
              {generatedResponse ? (
                <StrategyPreview
                  response={generatedResponse}
                  onSaved={handleSaved}
                  onClear={handleClear}
                />
              ) : (
                <Card className="bg-slate-800/50 border-slate-700 border-dashed h-full min-h-[400px] flex items-center justify-center">
                  <CardContent className="text-center py-12">
                    <Sparkles className="w-12 h-12 mx-auto text-slate-600 mb-4" />
                    <h3 className="font-medium text-slate-400 mb-2">
                      No Strategy Generated Yet
                    </h3>
                    <p className="text-sm text-slate-500 max-w-sm mx-auto">
                      Describe your trading strategy on the left panel and click
                      &quot;Generate&quot; to create an AI-powered strategy.
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>

        {/* Library Tab */}
        <TabsContent value="library" className="space-y-6">
          {/* Quick Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-500/20 rounded-lg">
                    <FolderOpen className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Total Strategies</p>
                    <p className="text-2xl font-bold text-white">{strategies.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-500/20 rounded-lg">
                    <Bot className="w-5 h-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Active</p>
                    <p className="text-2xl font-bold text-green-400">{activeStrategies.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-800 border-slate-700">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-yellow-500/20 rounded-lg">
                    <Sparkles className="w-5 h-5 text-yellow-400" />
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">AI Generated</p>
                    <p className="text-2xl font-bold text-yellow-400">{aiGeneratedStrategies.length}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Strategy List */}
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-32 w-full" />
              ))}
            </div>
          ) : strategies.length === 0 ? (
            <Card className="bg-slate-800/50 border-slate-700 border-dashed">
              <CardContent className="text-center py-12">
                <Bot className="w-12 h-12 mx-auto text-slate-600 mb-4" />
                <h3 className="font-medium text-slate-400 mb-2">
                  No Strategies Yet
                </h3>
                <p className="text-sm text-slate-500 mb-4">
                  Create your first trading strategy using the AI Builder
                </p>
                <Button onClick={() => setActiveTab("builder")}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Strategy
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {strategies.map((strategy) => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  onSelect={handleSelectStrategy}
                  onBacktest={handleBacktest}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
