"use client";

import { useState } from "react";
import {
  useMLModels,
  useCreateMLModel,
  useToggleMLModel,
  useTrainMLModel,
  useDeleteMLModel,
} from "@/hooks/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

export default function BotsPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newModel, setNewModel] = useState({
    name: "",
    model_type: "random_forest",
    symbol: "EURUSD",
    timeframe: "H1",
  });

  // API hooks
  const { data: models = [], isLoading } = useMLModels();
  const createModelMutation = useCreateMLModel();
  const toggleModelMutation = useToggleMLModel();
  const trainModelMutation = useTrainMLModel();
  const deleteModelMutation = useDeleteMLModel();

  const handleCreateModel = async () => {
    await createModelMutation.mutateAsync({
      name: newModel.name,
      model_type: newModel.model_type,
      config: {
        symbol: newModel.symbol,
        timeframe: newModel.timeframe,
      },
    });

    setShowCreateModal(false);
    setNewModel({ name: "", model_type: "random_forest", symbol: "EURUSD", timeframe: "H1" });
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

  const handleDelete = async (modelId: string) => {
    if (confirm("Are you sure you want to delete this model?")) {
      await deleteModelMutation.mutateAsync(modelId);
    }
  };

  // Calculate stats
  const activeModels = models.filter((m) => m.is_active).length;
  const avgAccuracy =
    models.length > 0
      ? models.reduce((acc, m) => acc + (m.performance_metrics?.accuracy || 0), 0) /
        models.length
      : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">ML Trading Bots</h1>
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
        <StatCard label="Predictions Today" value="0" icon="💡" />
      </div>

      {/* Models List */}
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
                <div key={model.id} className="py-4 hover:bg-accent/50 px-2 rounded-lg">
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
                          {model.model_type.replace("_", " ").toUpperCase()} •{" "}
                          {new Date(model.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      {/* Metrics */}
                      {model.performance_metrics && (
                        <div className="flex gap-4 text-sm">
                          <div className="text-center">
                            <p className="text-muted-foreground">Accuracy</p>
                            <p className="font-semibold">
                              {(model.performance_metrics.accuracy! * 100).toFixed(1)}%
                            </p>
                          </div>
                          <div className="text-center">
                            <p className="text-muted-foreground">Precision</p>
                            <p className="font-semibold">
                              {(model.performance_metrics.precision! * 100).toFixed(1)}%
                            </p>
                          </div>
                          <div className="text-center">
                            <p className="text-muted-foreground">F1</p>
                            <p className="font-semibold">
                              {(model.performance_metrics.f1_score! * 100).toFixed(1)}%
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant={model.is_active ? "default" : "outline"}
                          onClick={() => handleToggleActive(model.id, model.is_active)}
                          disabled={toggleModelMutation.isPending}
                        >
                          {model.is_active ? "Active" : "Activate"}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleTrain(model.id)}
                          disabled={trainModelMutation.isPending}
                        >
                          Train
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDelete(model.id)}
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
    </div>
  );
}
