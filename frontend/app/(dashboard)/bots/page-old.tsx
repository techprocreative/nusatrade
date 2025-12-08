"use client";

import { useState, useEffect } from "react";

interface MLModel {
  id: string;
  name: string;
  model_type: string;
  is_active: boolean;
  performance_metrics: {
    accuracy?: number;
    precision?: number;
    f1_score?: number;
  } | null;
  created_at: string;
}

export default function BotsPage() {
  const [models, setModels] = useState<MLModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newModel, setNewModel] = useState({
    name: "",
    model_type: "random_forest",
    symbol: "EURUSD",
    timeframe: "H1",
  });

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    setIsLoading(true);
    try {
      // TODO: Replace with actual API call
      // const response = await fetch("/api/v1/ml/models");
      // const data = await response.json();

      // Sample data for demo
      setModels([
        {
          id: "1",
          name: "EURUSD Trend Predictor",
          model_type: "random_forest",
          is_active: true,
          performance_metrics: {
            accuracy: 0.68,
            precision: 0.71,
            f1_score: 0.65,
          },
          created_at: new Date().toISOString(),
        },
        {
          id: "2",
          name: "Scalping Bot v2",
          model_type: "gradient_boosting",
          is_active: false,
          performance_metrics: {
            accuracy: 0.62,
            precision: 0.58,
            f1_score: 0.60,
          },
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (error) {
      console.error("Failed to fetch models:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateModel = async () => {
    try {
      // TODO: Call API
      const newModelData: MLModel = {
        id: Date.now().toString(),
        name: newModel.name,
        model_type: newModel.model_type,
        is_active: false,
        performance_metrics: null,
        created_at: new Date().toISOString(),
      };
      setModels([...models, newModelData]);
      setShowCreateModal(false);
      setNewModel({ name: "", model_type: "random_forest", symbol: "EURUSD", timeframe: "H1" });
    } catch (error) {
      console.error("Failed to create model:", error);
    }
  };

  const handleToggleActive = async (modelId: string, currentStatus: boolean) => {
    setModels(models.map(m =>
      m.id === modelId ? { ...m, is_active: !currentStatus } :
        !currentStatus ? { ...m, is_active: false } : m
    ));
  };

  const handleTrain = async (modelId: string) => {
    alert(`Training started for model ${modelId}. This may take a few minutes.`);
  };

  const handleDelete = async (modelId: string) => {
    if (confirm("Are you sure you want to delete this model?")) {
      setModels(models.filter(m => m.id !== modelId));
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">ML Trading Bots</h1>
          <p className="text-slate-400 mt-1">Manage and train machine learning models for automated trading</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold"
        >
          + Create Model
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Models"
          value={models.length.toString()}
          icon="🤖"
        />
        <StatCard
          label="Active Bots"
          value={models.filter(m => m.is_active).length.toString()}
          icon="🟢"
          color="green"
        />
        <StatCard
          label="Avg Accuracy"
          value={`${(models.reduce((acc, m) => acc + (m.performance_metrics?.accuracy || 0), 0) / Math.max(models.length, 1) * 100).toFixed(1)}%`}
          icon="📊"
          color="blue"
        />
        <StatCard
          label="Predictions Today"
          value="0"
          icon="💡"
        />
      </div>

      {/* Models List */}
      <div className="bg-slate-800 rounded-lg border border-slate-700">
        <div className="p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">Your Models</h2>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-slate-400">Loading models...</div>
        ) : models.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <p>No models yet. Create your first ML trading bot!</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-700">
            {models.map((model) => (
              <div key={model.id} className="p-4 hover:bg-slate-700/50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-3 h-3 rounded-full ${model.is_active ? "bg-green-500" : "bg-slate-500"}`} />
                    <div>
                      <h3 className="text-white font-medium">{model.name}</h3>
                      <p className="text-sm text-slate-400">
                        {model.model_type.replace("_", " ").toUpperCase()} • Created {new Date(model.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    {/* Metrics */}
                    {model.performance_metrics && (
                      <div className="flex gap-4 text-sm">
                        <div className="text-center">
                          <p className="text-slate-400">Accuracy</p>
                          <p className="text-white font-semibold">{(model.performance_metrics.accuracy! * 100).toFixed(1)}%</p>
                        </div>
                        <div className="text-center">
                          <p className="text-slate-400">Precision</p>
                          <p className="text-white font-semibold">{(model.performance_metrics.precision! * 100).toFixed(1)}%</p>
                        </div>
                        <div className="text-center">
                          <p className="text-slate-400">F1 Score</p>
                          <p className="text-white font-semibold">{(model.performance_metrics.f1_score! * 100).toFixed(1)}%</p>
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleToggleActive(model.id, model.is_active)}
                        className={`px-3 py-1 rounded text-sm font-medium ${model.is_active
                            ? "bg-green-600/20 text-green-400 hover:bg-green-600/30"
                            : "bg-slate-600 text-slate-300 hover:bg-slate-500"
                          }`}
                      >
                        {model.is_active ? "Active" : "Activate"}
                      </button>
                      <button
                        onClick={() => handleTrain(model.id)}
                        className="px-3 py-1 bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 rounded text-sm font-medium"
                      >
                        Train
                      </button>
                      <button
                        onClick={() => handleDelete(model.id)}
                        className="px-3 py-1 bg-red-600/20 text-red-400 hover:bg-red-600/30 rounded text-sm font-medium"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Model Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 w-full max-w-md border border-slate-700">
            <h2 className="text-xl font-bold text-white mb-4">Create New Model</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Model Name</label>
                <input
                  type="text"
                  value={newModel.name}
                  onChange={(e) => setNewModel({ ...newModel, name: e.target.value })}
                  placeholder="e.g., EURUSD Scalper"
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                />
              </div>

              <div>
                <label className="block text-sm text-slate-400 mb-1">Model Type</label>
                <select
                  value={newModel.model_type}
                  onChange={(e) => setNewModel({ ...newModel, model_type: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                >
                  <option value="random_forest">Random Forest</option>
                  <option value="gradient_boosting">Gradient Boosting</option>
                  <option value="lstm">LSTM (Coming Soon)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Symbol</label>
                  <select
                    value={newModel.symbol}
                    onChange={(e) => setNewModel({ ...newModel, symbol: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  >
                    <option value="EURUSD">EURUSD</option>
                    <option value="GBPUSD">GBPUSD</option>
                    <option value="USDJPY">USDJPY</option>
                    <option value="XAUUSD">XAUUSD</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Timeframe</label>
                  <select
                    value={newModel.timeframe}
                    onChange={(e) => setNewModel({ ...newModel, timeframe: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  >
                    <option value="M15">M15</option>
                    <option value="M30">M30</option>
                    <option value="H1">H1</option>
                    <option value="H4">H4</option>
                    <option value="D1">D1</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateModel}
                disabled={!newModel.name}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-white font-semibold"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: string; icon: string; color?: string }) {
  const colorClasses: Record<string, string> = {
    green: "text-green-500",
    blue: "text-blue-500",
    red: "text-red-500",
  };

  return (
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <div className="flex items-center gap-3">
        <span className="text-2xl">{icon}</span>
        <div>
          <p className="text-sm text-slate-400">{label}</p>
          <p className={`text-xl font-bold ${color ? colorClasses[color] : "text-white"}`}>
            {value}
          </p>
        </div>
      </div>
    </div>
  );
}
