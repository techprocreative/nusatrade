"use client";

import { useState } from "react";
import {
  useMLModels,
  useCreateMLModel,
  useToggleMLModel,
  useTrainMLModel,
  useDeleteMLModel,
  useGetPrediction,
  useExecutePrediction,
  useStrategies,
} from "@/hooks/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import type { MLModel, MLPrediction } from "@/types";
import { TrendingUp, TrendingDown, Zap, Brain, Target } from "lucide-react";

function StatCard({ label, value, icon, color }: { 
  label: string; 
  value: string; 
  icon: string; 
  color?: string 
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className={`text-xl font-bold ${color || ""}`}>{value}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PredictionCard({ 
  prediction, 
  onExecute, 
  isExecuting 
}: { 
  prediction: MLPrediction; 
  onExecute: (lotSize: number) => void;
  isExecuting: boolean;
}) {
  const [lotSize, setLotSize] = useState("0.1");
  const pred = prediction.prediction;
  const isHold = pred.direction === "HOLD";

  return (
    <Card className="border-2 border-primary/50">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-500" />
            ML Signal
          </span>
          <Badge variant={pred.direction === "BUY" ? "default" : pred.direction === "SELL" ? "destructive" : "secondary"}>
            {pred.direction}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Confidence</span>
          <span className={`font-bold ${pred.confidence >= 0.7 ? "text-green-500" : pred.confidence >= 0.5 ? "text-yellow-500" : "text-red-500"}`}>
            {(pred.confidence * 100).toFixed(1)}%
          </span>
        </div>

        {!isHold && (
          <>
            <div className="grid grid-cols-3 gap-2 text-sm">
              <div className="text-center p-2 bg-muted rounded">
                <p className="text-muted-foreground">Entry</p>
                <p className="font-semibold">{pred.entry_price?.toFixed(5)}</p>
              </div>
              <div className="text-center p-2 bg-red-500/10 rounded">
                <p className="text-muted-foreground">SL</p>
                <p className="font-semibold text-red-500">{pred.stop_loss?.toFixed(5)}</p>
              </div>
              <div className="text-center p-2 bg-green-500/10 rounded">
                <p className="text-muted-foreground">TP</p>
                <p className="font-semibold text-green-500">{pred.take_profit?.toFixed(5)}</p>
              </div>
            </div>

            {pred.risk_reward_ratio && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Risk:Reward</span>
                <span className="font-semibold">1:{pred.risk_reward_ratio}</span>
              </div>
            )}

            {prediction.strategy_rules && (
              <div className="text-xs p-2 bg-blue-500/10 rounded border border-blue-500/20">
                <p className="text-blue-400 font-medium mb-1">Strategy Rules:</p>
                {prediction.strategy_rules.entry_rules.length > 0 && (
                  <p className="text-muted-foreground">Entry: {prediction.strategy_rules.entry_rules.join(", ")}</p>
                )}
                {prediction.strategy_rules.exit_rules.length > 0 && (
                  <p className="text-muted-foreground">Exit: {prediction.strategy_rules.exit_rules.join(", ")}</p>
                )}
              </div>
            )}

            <div className="flex gap-2 items-end">
              <div className="flex-1 space-y-1">
                <Label className="text-xs">Lot Size</Label>
                <Input 
                  type="number" 
                  step="0.01" 
                  min="0.01" 
                  max="10"
                  value={lotSize}
                  onChange={(e) => setLotSize(e.target.value)}
                />
              </div>
              <Button 
                onClick={() => onExecute(parseFloat(lotSize))}
                disabled={isExecuting}
                className="flex-1"
                variant={pred.direction === "BUY" ? "default" : "destructive"}
              >
                {isExecuting ? "Executing..." : `Execute ${pred.direction}`}
              </Button>
            </div>
          </>
        )}

        {isHold && (
          <p className="text-center text-muted-foreground py-4">
            Model suggests no action at this time
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function BotsPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [deleteModelId, setDeleteModelId] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<MLModel | null>(null);
  const [currentPrediction, setCurrentPrediction] = useState<MLPrediction | null>(null);
  const [newModel, setNewModel] = useState({
    name: "",
    model_type: "random_forest",
    symbol: "EURUSD",
    timeframe: "H1",
    strategy_id: "",
  });

  // API hooks
  const { data: models = [], isLoading } = useMLModels();
  const { data: strategies = [] } = useStrategies();
  const createModelMutation = useCreateMLModel();
  const toggleModelMutation = useToggleMLModel();
  const trainModelMutation = useTrainMLModel();
  const deleteModelMutation = useDeleteMLModel();
  const getPredictionMutation = useGetPrediction();
  const executePredictionMutation = useExecutePrediction();

  const handleCreateModel = async () => {
    await createModelMutation.mutateAsync({
      name: newModel.name,
      model_type: newModel.model_type,
      symbol: newModel.symbol,
      timeframe: newModel.timeframe,
      strategy_id: newModel.strategy_id || undefined,
    });

    setShowCreateModal(false);
    setNewModel({ name: "", model_type: "random_forest", symbol: "EURUSD", timeframe: "H1", strategy_id: "" });
  };

  const handleToggleActive = async (modelId: string, currentStatus: boolean) => {
    await toggleModelMutation.mutateAsync({
      modelId,
      isActive: !currentStatus,
    });
  };

  const handleTrain = async (modelId: string) => {
    await trainModelMutation.mutateAsync(modelId);
  };

  const handleDelete = async () => {
    if (deleteModelId) {
      await deleteModelMutation.mutateAsync(deleteModelId);
      setDeleteModelId(null);
      if (selectedModel?.id === deleteModelId) {
        setSelectedModel(null);
        setCurrentPrediction(null);
      }
    }
  };

  const handleSelectModel = (model: MLModel) => {
    setSelectedModel(model);
    setCurrentPrediction(null);
  };

  const handleGetPrediction = async () => {
    if (!selectedModel) return;
    const result = await getPredictionMutation.mutateAsync({
      modelId: selectedModel.id,
      symbol: selectedModel.symbol || "EURUSD",
    });
    setCurrentPrediction(result);
  };

  const handleExecuteTrade = async (lotSize: number) => {
    if (!selectedModel || !currentPrediction) return;
    await executePredictionMutation.mutateAsync({
      modelId: selectedModel.id,
      predictionId: currentPrediction.id,
      lotSize,
    });
  };

  // Calculate stats
  const activeModels = models.filter((m) => m.is_active).length;
  const avgAccuracy =
    models.length > 0
      ? models.reduce((acc, m) => acc + (m.performance_metrics?.accuracy || 0), 0) /
        models.length
      : 0;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="w-6 h-6" />
            ML Trading Bots
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage and train machine learning models for automated trading
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>+ Create Model</Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard label="Total Models" value={models.length.toString()} icon="🤖" />
        <StatCard
          label="Active Bots"
          value={activeModels.toString()}
          icon="🟢"
          color="text-green-500"
        />
        <StatCard
          label="Avg Accuracy"
          value={`${(avgAccuracy * 100).toFixed(1)}%`}
          icon="📊"
          color="text-blue-500"
        />
        <StatCard label="With Strategy" value={models.filter(m => m.strategy_id).length.toString()} icon="📋" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Models List */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Your Models</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="text-center py-8 text-muted-foreground">Loading models...</div>
              ) : models.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No models yet. Create your first ML trading bot!</p>
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {models.map((model) => (
                    <div 
                      key={model.id} 
                      className={`py-4 px-2 rounded-lg cursor-pointer transition-colors ${
                        selectedModel?.id === model.id ? "bg-accent" : "hover:bg-accent/50"
                      }`}
                      onClick={() => handleSelectModel(model)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div
                            className={`w-3 h-3 rounded-full ${
                              model.is_active ? "bg-green-500" : "bg-muted"
                            }`}
                          />
                          <div>
                            <h3 className="font-medium">{model.name}</h3>
                            <p className="text-sm text-muted-foreground">
                              {model.model_type.replace("_", " ").toUpperCase()} • {model.symbol} • {model.timeframe}
                              {model.strategy_name && (
                                <span className="ml-2 text-blue-400">• {model.strategy_name}</span>
                              )}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          {/* Metrics */}
                          {model.performance_metrics && (
                            <div className="hidden md:flex gap-4 text-sm">
                              <div className="text-center">
                                <p className="text-muted-foreground text-xs">Accuracy</p>
                                <p className="font-semibold">
                                  {(model.performance_metrics.accuracy! * 100).toFixed(1)}%
                                </p>
                              </div>
                            </div>
                          )}

                          {/* Actions */}
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant={model.is_active ? "default" : "outline"}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleToggleActive(model.id, model.is_active);
                              }}
                              disabled={toggleModelMutation.isPending}
                            >
                              {model.is_active ? "Active" : "Activate"}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleTrain(model.id);
                              }}
                              disabled={trainModelMutation.isPending}
                            >
                              Train
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeleteModelId(model.id);
                              }}
                              disabled={deleteModelMutation.isPending}
                            >
                              Delete
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Prediction Panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="w-5 h-5" />
                Get Signal
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selectedModel ? (
                <div className="space-y-4">
                  <div className="p-3 bg-muted rounded-lg">
                    <p className="font-medium">{selectedModel.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {selectedModel.symbol} • {selectedModel.timeframe}
                    </p>
                    {selectedModel.strategy_name && (
                      <p className="text-sm text-blue-400">Strategy: {selectedModel.strategy_name}</p>
                    )}
                  </div>

                  <Button 
                    onClick={handleGetPrediction}
                    disabled={getPredictionMutation.isPending}
                    className="w-full"
                  >
                    {getPredictionMutation.isPending ? "Generating..." : "Get ML Signal"}
                  </Button>
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-4">
                  Select a model to get predictions
                </p>
              )}
            </CardContent>
          </Card>

          {currentPrediction && (
            <PredictionCard 
              prediction={currentPrediction}
              onExecute={handleExecuteTrade}
              isExecuting={executePredictionMutation.isPending}
            />
          )}
        </div>
      </div>

      {/* Create Model Dialog */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Model</DialogTitle>
            <DialogDescription>
              Configure a new machine learning model for trading
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Model Name</Label>
              <Input
                id="name"
                value={newModel.name}
                onChange={(e) => setNewModel({ ...newModel, name: e.target.value })}
                placeholder="e.g., EURUSD Scalper"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="model_type">Model Type</Label>
              <Select
                value={newModel.model_type}
                onValueChange={(value) => setNewModel({ ...newModel, model_type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="random_forest">Random Forest</SelectItem>
                  <SelectItem value="gradient_boosting">Gradient Boosting</SelectItem>
                  <SelectItem value="lstm">LSTM (Coming Soon)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="symbol">Symbol</Label>
                <Select
                  value={newModel.symbol}
                  onValueChange={(value) => setNewModel({ ...newModel, symbol: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EURUSD">EURUSD</SelectItem>
                    <SelectItem value="GBPUSD">GBPUSD</SelectItem>
                    <SelectItem value="USDJPY">USDJPY</SelectItem>
                    <SelectItem value="XAUUSD">XAUUSD</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="timeframe">Timeframe</Label>
                <Select
                  value={newModel.timeframe}
                  onValueChange={(value) => setNewModel({ ...newModel, timeframe: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="M15">M15</SelectItem>
                    <SelectItem value="M30">M30</SelectItem>
                    <SelectItem value="H1">H1</SelectItem>
                    <SelectItem value="H4">H4</SelectItem>
                    <SelectItem value="D1">D1</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="strategy">Link to Strategy (Optional)</Label>
              <Select
                value={newModel.strategy_id}
                onValueChange={(value) => setNewModel({ ...newModel, strategy_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a strategy" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">No Strategy</SelectItem>
                  {strategies.map((s) => (
                    <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Model will use strategy&apos;s risk management settings for SL/TP calculations
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateModel}
              disabled={!newModel.name || createModelMutation.isPending}
            >
              {createModelMutation.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={!!deleteModelId}
        onOpenChange={(open) => !open && setDeleteModelId(null)}
        title="Delete Model"
        description="Are you sure you want to delete this model? This action cannot be undone."
        confirmText="Delete"
        variant="destructive"
        onConfirm={handleDelete}
        isLoading={deleteModelMutation.isPending}
      />
    </div>
  );
}
