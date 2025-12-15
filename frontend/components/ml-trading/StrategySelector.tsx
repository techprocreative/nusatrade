"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Loader2, AlertCircle, CheckCircle2, Sparkles } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  getStrategiesForSymbol,
  linkModelToStrategy,
  getStrategyTemplates,
  createStrategyFromTemplate,
  type MLModel,
  type Strategy,
} from "@/lib/api/ml-models";

interface StrategySelectorProps {
  model: MLModel;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function StrategySelector({ model, open, onClose, onSuccess }: StrategySelectorProps) {
  const [selectedStrategy, setSelectedStrategy] = useState<string>("");
  const [showTemplates, setShowTemplates] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const token = typeof window !== 'undefined' ? localStorage.getItem("token") || "" : "";

  // Fetch strategies for model's symbol
  const { data: strategiesData, isLoading: loadingStrategies } = useQuery({
    queryKey: ["strategies", model.symbol],
    queryFn: () => getStrategiesForSymbol(model.symbol, token),
    enabled: open,
  });

  // Fetch templates
  const { data: templatesData } = useQuery({
    queryKey: ["strategy-templates"],
    queryFn: () => getStrategyTemplates(token),
    enabled: showTemplates,
  });

  // Link strategy mutation
  const linkMutation = useMutation({
    mutationFn: () => linkModelToStrategy(model.id, selectedStrategy, token),
    onSuccess: () => {
      toast({
        title: "Strategy Linked",
        description: "Model successfully linked to strategy",
      });
      queryClient.invalidateQueries({ queryKey: ["ml-models"] });
      onSuccess();
      onClose();
    },
    onError: (error: Error) => {
      toast({
        title: "Link Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Create from template mutation
  const createFromTemplateMutation = useMutation({
    mutationFn: () => createStrategyFromTemplate(selectedTemplate, model.symbol, null, token),
    onSuccess: (newStrategy) => {
      toast({
        title: "Strategy Created",
        description: `Created ${newStrategy.name} from template`,
      });
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      setSelectedStrategy(newStrategy.id);
      setShowTemplates(false);
    },
    onError: (error: Error) => {
      toast({
        title: "Creation Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const handleLink = () => {
    if (!selectedStrategy) {
      toast({
        title: "No Strategy Selected",
        description: "Please select a strategy first",
        variant: "destructive",
      });
      return;
    }
    linkMutation.mutate();
  };

  const handleCreateFromTemplate = () => {
    if (!selectedTemplate) return;
    createFromTemplateMutation.mutate();
  };

  const strategies = strategiesData || [];
  const templates = templatesData?.templates || [];

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Link Strategy to Model</DialogTitle>
          <DialogDescription>
            Select a strategy for {model.name} ({model.symbol})
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {!showTemplates ? (
            <>
              {/* Existing Strategies */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Select Existing Strategy</label>
                {loadingStrategies ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading strategies...
                  </div>
                ) : strategies.length > 0 ? (
                  <Select value={selectedStrategy} onValueChange={setSelectedStrategy}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a strategy..." />
                    </SelectTrigger>
                    <SelectContent>
                      {strategies.map((strategy) => (
                        <SelectItem key={strategy.id} value={strategy.id}>
                          <div className="flex flex-col">
                            <span className="font-medium">{strategy.name}</span>
                            <span className="text-xs text-muted-foreground">
                              {strategy.description}
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      No strategies found for {model.symbol}.
                      Create one using a template below.
                    </AlertDescription>
                  </Alert>
                )}
              </div>

              {/* Or Create New */}
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-background px-2 text-muted-foreground">Or</span>
                </div>
              </div>

              <Button
                variant="outline"
                className="w-full"
                onClick={() => setShowTemplates(true)}
              >
                <Sparkles className="mr-2 h-4 w-4" />
                Create from Template
              </Button>
            </>
          ) : (
            <>
              {/* Template Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Choose Template</label>
                <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select template..." />
                  </SelectTrigger>
                  <SelectContent>
                    {templates.map((template: any) => (
                      <SelectItem key={template.id} value={template.id}>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{template.name}</span>
                          <Badge variant="outline">{template.risk_level}</Badge>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {selectedTemplate && (
                <Alert>
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertDescription>
                    {templates.find((t: any) => t.id === selectedTemplate)?.description}
                  </AlertDescription>
                </Alert>
              )}

              <Button
                variant="outline"
                className="w-full"
                onClick={() => setShowTemplates(false)}
              >
                Back to Strategy Selection
              </Button>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          {!showTemplates ? (
            <Button
              onClick={handleLink}
              disabled={!selectedStrategy || linkMutation.isPending}
            >
              {linkMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Link Strategy
            </Button>
          ) : (
            <Button
              onClick={handleCreateFromTemplate}
              disabled={!selectedTemplate || createFromTemplateMutation.isPending}
            >
              {createFromTemplateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create & Link
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
