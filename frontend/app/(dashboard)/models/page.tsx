"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Star,
  TrendingUp,
  Target,
  BarChart3,
  Settings,
  AlertCircle,
  CheckCircle2,
  Info,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface Model {
  model_id: string;
  model_path: string;
  symbol: string;
  file_size: number;
  created_at: string;
  metadata: {
    win_rate?: number;
    profit_factor?: number;
    accuracy?: number;
  };
}

interface DefaultModel {
  model_path: string;
  model_id: string;
  symbol: string;
  is_user_override: boolean;
  win_rate?: number;
  profit_factor?: number;
  accuracy?: number;
  total_trades?: number;
}

export default function ModelsPage() {
  const [selectedSymbol, setSelectedSymbol] = useState("XAUUSD");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Fetch models for selected symbol
  const { data: symbolData, isLoading } = useQuery({
    queryKey: ["models", selectedSymbol],
    queryFn: async () => {
      const res = await fetch(`${API_BASE_URL}/api/v1/ml-models/models/${selectedSymbol}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
      });
      if (!res.ok) throw new Error("Failed to fetch models");
      return res.json();
    }
  });

  // Set user default mutation
  const setDefaultMutation = useMutation({
    mutationFn: async ({ symbol, model }: { symbol: string; model: Model }) => {
      const res = await fetch(`${API_BASE_URL}/api/v1/ml-models/defaults/${symbol}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({
          model_path: model.model_path,
          model_id: model.model_id
        })
      });
      if (!res.ok) throw new Error("Failed to set default");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      toast({
        title: "Default Model Updated",
        description: "Successfully set as your default model for this symbol"
      });
    }
  });

  // Reset to system default mutation
  const resetDefaultMutation = useMutation({
    mutationFn: async (symbol: string) => {
      const res = await fetch(`${API_BASE_URL}/api/v1/ml-models/defaults/${symbol}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
      });
      if (!res.ok) throw new Error("Failed to reset");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      toast({
        title: "Reset to System Default",
        description: "Now using system default model"
      });
    }
  });

  const models: Model[] = symbolData?.models || [];
  const systemDefault: DefaultModel | null = symbolData?.system_default || null;
  const userDefault: DefaultModel | null = symbolData?.user_default || null;

  const isModelDefault = (model: Model) => {
    const activeDefault = userDefault || systemDefault;
    return activeDefault?.model_id === model.model_id;
  };

  const isUserOverride = (model: Model) => {
    return userDefault?.model_id === model.model_id;
  };

  const formatFileSize = (bytes: number) => {
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-blue-500" />
            Model Defaults
          </h1>
          <p className="text-muted-foreground mt-1">
            Set default ML models for each trading symbol. Auto-trading will use these models when generating predictions.
          </p>
        </div>
      </div>

      {/* Info Card */}
      <Alert className="bg-blue-500/10 border-blue-500/30">
        <Info className="h-4 w-4 text-blue-500" />
        <AlertDescription className="text-sm text-slate-300">
          <strong>How it works:</strong> Each symbol (XAUUSD, EURUSD, BTCUSD) has a system default model.
          You can override the default by selecting your preferred model. Auto-trading and ML predictions will
          automatically use the active default for each symbol.
        </AlertDescription>
      </Alert>

      {/* Symbol Tabs */}
      <Tabs value={selectedSymbol} onValueChange={setSelectedSymbol}>
        <TabsList className="bg-slate-800 border border-slate-700">
          <TabsTrigger value="XAUUSD">XAUUSD (Gold)</TabsTrigger>
          <TabsTrigger value="EURUSD">EURUSD (Forex)</TabsTrigger>
          <TabsTrigger value="BTCUSD">BTCUSD (Crypto)</TabsTrigger>
        </TabsList>

        <TabsContent value={selectedSymbol} className="space-y-4">
          {/* Current Default Card */}
          {(systemDefault || userDefault) && (
            <Card className="border-blue-500/20 bg-slate-800/50">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Star className="w-5 h-5 text-yellow-500" />
                  Current Default Model
                  {userDefault && (
                    <Badge variant="outline" className="ml-2 bg-blue-500/10 text-blue-400 border-blue-500/30">
                      Your Override
                    </Badge>
                  )}
                  {!userDefault && systemDefault && (
                    <Badge variant="outline" className="ml-2 bg-green-500/10 text-green-400 border-green-500/30">
                      System Default
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-slate-900/50 rounded-lg p-3">
                    <div className="text-xs text-slate-400 mb-1">Model ID</div>
                    <div className="text-sm font-mono text-slate-300 truncate">
                      {(userDefault || systemDefault)?.model_id}
                    </div>
                  </div>

                  {(userDefault?.win_rate || systemDefault?.win_rate) && (
                    <div className="bg-slate-900/50 rounded-lg p-3">
                      <div className="text-xs text-slate-400 mb-1">Win Rate</div>
                      <div className="text-lg font-bold text-green-400 flex items-center gap-1">
                        <Target className="w-4 h-4" />
                        {((userDefault || systemDefault)?.win_rate || 0).toFixed(1)}%
                      </div>
                    </div>
                  )}

                  {(userDefault?.profit_factor || systemDefault?.profit_factor) && (
                    <div className="bg-slate-900/50 rounded-lg p-3">
                      <div className="text-xs text-slate-400 mb-1">Profit Factor</div>
                      <div className="text-lg font-bold text-green-400 flex items-center gap-1">
                        <TrendingUp className="w-4 h-4" />
                        {((userDefault || systemDefault)?.profit_factor || 0).toFixed(2)}
                      </div>
                    </div>
                  )}

                  {(userDefault?.accuracy || systemDefault?.accuracy) && (
                    <div className="bg-slate-900/50 rounded-lg p-3">
                      <div className="text-xs text-slate-400 mb-1">Accuracy</div>
                      <div className="text-lg font-bold text-blue-400">
                        {((userDefault || systemDefault)?.accuracy || 0).toFixed(1)}%
                      </div>
                    </div>
                  )}
                </div>

                {userDefault && (
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-blue-400" />
                    <p className="text-sm text-slate-400">
                      You have set a custom default model for {selectedSymbol}.
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => resetDefaultMutation.mutate(selectedSymbol)}
                      disabled={resetDefaultMutation.isPending}
                    >
                      Reset to System Default
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Available Models Table */}
          <Card className="bg-slate-800/50">
            <CardHeader>
              <CardTitle className="text-lg">Available Models</CardTitle>
              <CardDescription>
                {models.length > 0
                  ? `${models.length} model(s) available for ${selectedSymbol}. Click to set as your default.`
                  : `No models available for ${selectedSymbol} yet.`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="text-center py-8 text-slate-400">Loading models...</div>
              ) : models.length === 0 ? (
                <div className="text-center py-8">
                  <BarChart3 className="w-12 h-12 mx-auto text-slate-600 mb-2" />
                  <p className="text-slate-400">No models trained for {selectedSymbol} yet</p>
                  <p className="text-sm text-slate-500 mt-1">
                    Train a new model to see it here
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Model ID</TableHead>
                      <TableHead>Win Rate</TableHead>
                      <TableHead>Profit Factor</TableHead>
                      <TableHead>Accuracy</TableHead>
                      <TableHead>File Size</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {models.map((model) => (
                      <TableRow key={model.model_id}>
                        <TableCell className="font-mono text-sm">
                          <div className="max-w-[200px] truncate" title={model.model_id}>
                            {model.model_id}
                          </div>
                        </TableCell>
                        <TableCell>
                          {model.metadata.win_rate
                            ? `${model.metadata.win_rate.toFixed(1)}%`
                            : "N/A"}
                        </TableCell>
                        <TableCell>
                          {model.metadata.profit_factor?.toFixed(2) || "N/A"}
                        </TableCell>
                        <TableCell>
                          {model.metadata.accuracy
                            ? `${model.metadata.accuracy.toFixed(1)}%`
                            : "N/A"}
                        </TableCell>
                        <TableCell className="text-slate-400">
                          {formatFileSize(model.file_size)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {isModelDefault(model) && (
                              <Badge variant="default" className="bg-yellow-500/20 text-yellow-500 border-yellow-500/30">
                                <Star className="w-3 h-3 mr-1" />
                                DEFAULT
                              </Badge>
                            )}
                            {isUserOverride(model) && (
                              <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/30">
                                Your Choice
                              </Badge>
                            )}
                            {!isModelDefault(model) && !isUserOverride(model) && (
                              <span className="text-slate-500 text-sm">Available</span>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {!isUserOverride(model) && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setDefaultMutation.mutate({
                                symbol: selectedSymbol,
                                model
                              })}
                              disabled={setDefaultMutation.isPending}
                            >
                              <Settings className="w-4 h-4 mr-1" />
                              Set as Default
                            </Button>
                          )}
                          {isUserOverride(model) && (
                            <div className="flex items-center gap-1 text-green-400 text-sm">
                              <CheckCircle2 className="w-4 h-4" />
                              Active
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
