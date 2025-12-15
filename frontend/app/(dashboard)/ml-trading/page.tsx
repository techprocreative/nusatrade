"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Brain, AlertCircle, TrendingUp, Download, Loader2 } from "lucide-react";
import { ModelCard } from "@/components/ml-trading/ModelCard";
import { StrategySelector } from "@/components/ml-trading/StrategySelector";
import { getMLModels, importDefaultModel, type MLModel } from "@/lib/api/ml-models";
import { useToast } from "@/hooks/use-toast";

export default function MLTradingPage() {
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string>("XAUUSD");
  const [justImportedModel, setJustImportedModel] = useState<MLModel | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const token = typeof window !== 'undefined' ? localStorage.getItem("token") || "" : "";

  const { data: models, isLoading } = useQuery({
    queryKey: ["ml-models"],
    queryFn: () => getMLModels(token),
  });

  // Import default model mutation
  const importMutation = useMutation({
    mutationFn: (symbol: string) => importDefaultModel(symbol, token),
    onSuccess: (importedModel) => {
      toast({
        title: "Model Imported",
        description: `Successfully imported ${importedModel.symbol} default model. Now link a strategy to activate it.`,
      });
      queryClient.invalidateQueries({ queryKey: ["ml-models"] });
      setImportDialogOpen(false);

      // Auto-open strategy selector for the newly imported model
      setJustImportedModel(importedModel);
    },
    onError: (error: Error) => {
      toast({
        title: "Import Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleImport = () => {
    if (!selectedSymbol) {
      toast({
        title: "No Symbol Selected",
        description: "Please select a symbol first",
        variant: "destructive",
      });
      return;
    }
    importMutation.mutate(selectedSymbol);
  };

  const activeModels = models?.filter((m) => m.is_active) || [];
  const modelsWithoutStrategy = models?.filter((m) => m.is_active && !m.strategy_id) || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">ML Auto-Trading</h2>
          <p className="text-muted-foreground">
            Manage your ML models and trading strategies
          </p>
        </div>
        <Button onClick={() => setImportDialogOpen(true)}>
          <Download className="mr-2 h-4 w-4" />
          Import Default Model
        </Button>
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

      {/* Import Dialog */}
      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Import Default Model</DialogTitle>
            <DialogDescription>
              Import a pre-trained profitable model for a trading symbol
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Select Symbol</label>
              <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose symbol..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="XAUUSD">XAUUSD (Gold)</SelectItem>
                  <SelectItem value="EURUSD">EURUSD (Forex)</SelectItem>
                  <SelectItem value="BTCUSD">BTCUSD (Crypto)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Default models are pre-trained with profitable strategies. After importing,
                you'll need to link a strategy before activating the model.
              </AlertDescription>
            </Alert>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setImportDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleImport}
              disabled={importMutation.isPending}
            >
              {importMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Import Model
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Auto-open strategy selector for newly imported model */}
      {justImportedModel && (
        <StrategySelector
          model={justImportedModel}
          open={true}
          onClose={() => setJustImportedModel(null)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ["ml-models"] });
            setJustImportedModel(null);
          }}
        />
      )}
    </div>
  );
}
