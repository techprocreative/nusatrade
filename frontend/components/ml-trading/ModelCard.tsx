"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Power,
  PowerOff,
  Link as LinkIcon,
  AlertTriangle,
  TrendingUp,
  Target,
  Star,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { StrategySelector } from "./StrategySelector";
import { activateModel, deactivateModel, type MLModel } from "@/lib/api/ml-models";

interface ModelCardProps {
  model: MLModel;
}

export function ModelCard({ model }: ModelCardProps) {
  const [showStrategySelector, setShowStrategySelector] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const token = typeof window !== 'undefined' ? localStorage.getItem("token") || "" : "";

  // Activate mutation
  const activateMutation = useMutation({
    mutationFn: () => activateModel(model.id, token),
    onSuccess: () => {
      toast({
        title: "Model Activated",
        description: `${model.name} is now active for auto-trading`,
      });
      queryClient.invalidateQueries({ queryKey: ["ml-models"] });
    },
    onError: (error: Error) => {
      toast({
        title: "Activation Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Deactivate mutation
  const deactivateMutation = useMutation({
    mutationFn: () => deactivateModel(model.id, token),
    onSuccess: () => {
      toast({
        title: "Model Deactivated",
        description: `${model.name} is now inactive`,
      });
      queryClient.invalidateQueries({ queryKey: ["ml-models"] });
    },
  });

  const handleActivate = () => {
    if (!model.strategy_id) {
      toast({
        title: "Strategy Required",
        description: "Please link a strategy before activating",
        variant: "destructive",
      });
      setShowStrategySelector(true);
      return;
    }
    activateMutation.mutate();
  };

  const hasStrategy = !!model.strategy_id;
  const canActivate = hasStrategy && model.file_path;

  return (
    <>
      <Card className={model.is_active ? "border-green-500" : ""}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2">
                {model.name}
                {model.is_active && <Badge variant="default">Active</Badge>}
              </CardTitle>
              <CardDescription>
                {model.symbol} • {model.model_type}
              </CardDescription>
            </div>
            {model.is_active ? (
              <Button
                variant="outline"
                size="icon"
                onClick={() => deactivateMutation.mutate()}
                disabled={deactivateMutation.isPending}
              >
                <PowerOff className="h-4 w-4 text-red-500" />
              </Button>
            ) : (
              <Button
                variant="outline"
                size="icon"
                onClick={handleActivate}
                disabled={!canActivate || activateMutation.isPending}
              >
                <Power className="h-4 w-4 text-green-500" />
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Performance Metrics */}
          {model.performance_metrics && (
            <div className="grid grid-cols-3 gap-2 text-sm">
              {model.performance_metrics.accuracy && (
                <div className="flex items-center gap-1">
                  <Target className="h-3 w-3 text-muted-foreground" />
                  <span>{(model.performance_metrics.accuracy * 100).toFixed(1)}%</span>
                </div>
              )}
              {model.performance_metrics.win_rate && (
                <div className="flex items-center gap-1">
                  <TrendingUp className="h-3 w-3 text-muted-foreground" />
                  <span>{(model.performance_metrics.win_rate * 100).toFixed(1)}%</span>
                </div>
              )}
              {model.performance_metrics.profit_factor && (
                <div className="flex items-center gap-1">
                  <Star className="h-3 w-3 text-muted-foreground" />
                  <span>{model.performance_metrics.profit_factor.toFixed(2)}</span>
                </div>
              )}
            </div>
          )}

          {/* Strategy Status */}
          {hasStrategy ? (
            <Alert>
              <LinkIcon className="h-4 w-4" />
              <AlertDescription>
                Linked to: <strong>{model.strategy_name}</strong>
              </AlertDescription>
            </Alert>
          ) : (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                No strategy linked. Required for activation.
              </AlertDescription>
            </Alert>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            {!hasStrategy && (
              <Button
                variant="outline"
                className="w-full"
                onClick={() => setShowStrategySelector(true)}
              >
                <LinkIcon className="mr-2 h-4 w-4" />
                Link Strategy
              </Button>
            )}
            {hasStrategy && !model.is_active && (
              <Button
                className="w-full"
                onClick={handleActivate}
                disabled={activateMutation.isPending}
              >
                <Power className="mr-2 h-4 w-4" />
                Activate
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <StrategySelector
        model={model}
        open={showStrategySelector}
        onClose={() => setShowStrategySelector(false)}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ["ml-models"] })}
      />
    </>
  );
}
