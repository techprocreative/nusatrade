"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Brain, AlertCircle, TrendingUp } from "lucide-react";
import { ModelCard } from "@/components/ml-trading/ModelCard";
import { getMLModels } from "@/lib/api/ml-models";

export default function MLTradingPage() {
  const token = typeof window !== 'undefined' ? localStorage.getItem("token") || "" : "";

  const { data: models, isLoading } = useQuery({
    queryKey: ["ml-models"],
    queryFn: () => getMLModels(token),
  });

  const activeModels = models?.filter((m) => m.is_active) || [];
  const modelsWithoutStrategy = models?.filter((m) => m.is_active && !m.strategy_id) || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">ML Auto-Trading</h2>
        <p className="text-muted-foreground">
          Manage your ML models and trading strategies
        </p>
      </div>

      {/* Status Overview */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Models</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{models?.length || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Models</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeModels.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Need Strategy</CardTitle>
            <AlertCircle className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{modelsWithoutStrategy.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Warnings */}
      {modelsWithoutStrategy.length > 0 && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {modelsWithoutStrategy.length} active model(s) need strategy assignment.
            Link strategies to enable auto-trading.
          </AlertDescription>
        </Alert>
      )}

      {/* Models Grid */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Your ML Models</h3>
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-64" />
            ))}
          </div>
        ) : models && models.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {models.map((model) => (
              <ModelCard key={model.id} model={model} />
            ))}
          </div>
        ) : (
          <Alert>
            <Brain className="h-4 w-4" />
            <AlertDescription>
              No ML models found. Train a model or import a default model to get started.
            </AlertDescription>
          </Alert>
        )}
      </div>
    </div>
  );
}
