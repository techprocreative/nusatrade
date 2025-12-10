"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronDown, Calculator, Shield, TrendingUp } from "lucide-react";
import { useRiskProfiles, useCalculateSLTP } from "@/hooks/api/useTrading";
import type { TrailingStopSettings, CalculateSLTPResponse } from "@/types";

interface RiskManagementPanelProps {
  symbol: string;
  orderType: "BUY" | "SELL";
  entryPrice: number | null;
  onSLTPCalculated: (sl: number, tp: number) => void;
  onTrailingStopChange: (settings: TrailingStopSettings | null) => void;
}

export function RiskManagementPanel({
  symbol,
  orderType,
  entryPrice,
  onSLTPCalculated,
  onTrailingStopChange,
}: RiskManagementPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [riskProfile, setRiskProfile] = useState("moderate");
  const [useAutoSLTP, setUseAutoSLTP] = useState(false);
  const [slType, setSlType] = useState<"fixed_pips" | "atr_based" | "percentage">("atr_based");
  const [slValue, setSlValue] = useState("2.0");
  const [tpType, setTpType] = useState<"fixed_pips" | "risk_reward" | "atr_based">("risk_reward");
  const [tpValue, setTpValue] = useState("2.0");
  
  // Trailing stop settings
  const [trailingEnabled, setTrailingEnabled] = useState(false);
  const [trailingType, setTrailingType] = useState<"fixed_pips" | "atr_based" | "percentage">("atr_based");
  const [activationPips, setActivationPips] = useState("20");
  const [trailDistancePips, setTrailDistancePips] = useState("15");
  const [breakEvenEnabled, setBreakEvenEnabled] = useState(true);
  const [breakEvenPips, setBreakEvenPips] = useState("15");

  const [calculatedSLTP, setCalculatedSLTP] = useState<CalculateSLTPResponse | null>(null);

  const { data: profilesData } = useRiskProfiles();
  const calculateSLTPMutation = useCalculateSLTP();

  // Update settings when risk profile changes
  useEffect(() => {
    if (profilesData?.profiles && riskProfile) {
      const profile = profilesData.profiles[riskProfile];
      if (profile) {
        setSlType(profile.sl_type as any);
        setSlValue(profile.sl_value.toString());
        setTpType(profile.tp_type as any);
        setTpValue(profile.tp_value.toString());
        
        if (profile.trailing_stop) {
          setTrailingEnabled(profile.trailing_stop.enabled);
          setTrailingType(profile.trailing_stop.trailing_type);
          setActivationPips(profile.trailing_stop.activation_pips.toString());
          setTrailDistancePips(profile.trailing_stop.trail_distance_pips.toString());
          setBreakEvenEnabled(profile.trailing_stop.breakeven_enabled);
          setBreakEvenPips(profile.trailing_stop.breakeven_pips.toString());
        }
      }
    }
  }, [profilesData, riskProfile]);

  // Notify parent of trailing stop changes
  useEffect(() => {
    if (trailingEnabled) {
      onTrailingStopChange({
        enabled: true,
        trailing_type: trailingType,
        activation_pips: parseFloat(activationPips) || 20,
        trail_distance_pips: parseFloat(trailDistancePips) || 15,
        atr_multiplier: 1.5,
        breakeven_enabled: breakEvenEnabled,
        breakeven_pips: parseFloat(breakEvenPips) || 15,
      });
    } else {
      onTrailingStopChange(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trailingEnabled, trailingType, activationPips, trailDistancePips, breakEvenEnabled, breakEvenPips]);

  const handleCalculateSLTP = async () => {
    if (!entryPrice) return;
    
    try {
      const result = await calculateSLTPMutation.mutateAsync({
        symbol,
        direction: orderType,
        entry_price: entryPrice,
        sl_type: slType,
        sl_value: parseFloat(slValue) || 2.0,
        tp_type: tpType,
        tp_value: parseFloat(tpValue) || 2.0,
      });
      
      setCalculatedSLTP(result);
      onSLTPCalculated(result.stop_loss, result.take_profit);
    } catch (error) {
      console.error("Failed to calculate SL/TP:", error);
    }
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger asChild>
        <Button variant="ghost" className="w-full justify-between p-2 h-auto">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            <span className="text-sm font-medium">Risk Management</span>
          </div>
          <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`} />
        </Button>
      </CollapsibleTrigger>
      
      <CollapsibleContent className="space-y-4 pt-2">
        {/* Risk Profile Selector */}
        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">Risk Profile</Label>
          <Select value={riskProfile} onValueChange={setRiskProfile}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="conservative">Conservative (1% risk)</SelectItem>
              <SelectItem value="moderate">Moderate (2% risk)</SelectItem>
              <SelectItem value="aggressive">Aggressive (3% risk)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Auto SL/TP Toggle */}
        <div className="flex items-center justify-between">
          <Label className="text-xs">Auto Calculate SL/TP</Label>
          <Switch checked={useAutoSLTP} onCheckedChange={setUseAutoSLTP} />
        </div>

        {useAutoSLTP && (
          <>
            {/* Stop Loss Settings */}
            <div className="space-y-2 p-2 bg-muted/50 rounded">
              <Label className="text-xs font-medium">Stop Loss</Label>
              <div className="grid grid-cols-2 gap-2">
                <Select value={slType} onValueChange={(v) => setSlType(v as any)}>
                  <SelectTrigger className="h-7 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fixed_pips">Fixed Pips</SelectItem>
                    <SelectItem value="atr_based">ATR Based</SelectItem>
                    <SelectItem value="percentage">Percentage</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  type="number"
                  step="0.1"
                  value={slValue}
                  onChange={(e) => setSlValue(e.target.value)}
                  className="h-7 text-xs"
                  placeholder={slType === "atr_based" ? "ATR x" : "Pips"}
                />
              </div>
            </div>

            {/* Take Profit Settings */}
            <div className="space-y-2 p-2 bg-muted/50 rounded">
              <Label className="text-xs font-medium">Take Profit</Label>
              <div className="grid grid-cols-2 gap-2">
                <Select value={tpType} onValueChange={(v) => setTpType(v as any)}>
                  <SelectTrigger className="h-7 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fixed_pips">Fixed Pips</SelectItem>
                    <SelectItem value="risk_reward">Risk:Reward</SelectItem>
                    <SelectItem value="atr_based">ATR Based</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  type="number"
                  step="0.1"
                  value={tpValue}
                  onChange={(e) => setTpValue(e.target.value)}
                  className="h-7 text-xs"
                  placeholder={tpType === "risk_reward" ? "R:R" : "Pips"}
                />
              </div>
            </div>

            {/* Calculate Button */}
            <Button
              size="sm"
              variant="secondary"
              className="w-full h-8 text-xs"
              onClick={handleCalculateSLTP}
              disabled={!entryPrice || calculateSLTPMutation.isPending}
            >
              <Calculator className="h-3 w-3 mr-1" />
              {calculateSLTPMutation.isPending ? "Calculating..." : "Calculate SL/TP"}
            </Button>

            {/* Calculated Results */}
            {calculatedSLTP && (
              <div className="text-xs space-y-1 p-2 bg-green-500/10 rounded border border-green-500/20">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Stop Loss:</span>
                  <span className="font-mono text-red-500">{calculatedSLTP.stop_loss.toFixed(5)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Take Profit:</span>
                  <span className="font-mono text-green-500">{calculatedSLTP.take_profit.toFixed(5)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Risk:Reward:</span>
                  <span className="font-mono">1:{calculatedSLTP.risk_reward_ratio}</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>SL: {calculatedSLTP.sl_distance_pips} pips</span>
                  <span>TP: {calculatedSLTP.tp_distance_pips} pips</span>
                </div>
              </div>
            )}
          </>
        )}

        {/* Trailing Stop Settings */}
        <div className="space-y-2 p-2 bg-blue-500/10 rounded border border-blue-500/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              <Label className="text-xs font-medium">Trailing Stop</Label>
            </div>
            <Switch checked={trailingEnabled} onCheckedChange={setTrailingEnabled} />
          </div>

          {trailingEnabled && (
            <div className="space-y-2 pt-2">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label className="text-xs text-muted-foreground">Activation (pips)</Label>
                  <Input
                    type="number"
                    value={activationPips}
                    onChange={(e) => setActivationPips(e.target.value)}
                    className="h-7 text-xs"
                  />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Trail Distance</Label>
                  <Input
                    type="number"
                    value={trailDistancePips}
                    onChange={(e) => setTrailDistancePips(e.target.value)}
                    className="h-7 text-xs"
                  />
                </div>
              </div>
              
              <div className="flex items-center justify-between pt-1">
                <Label className="text-xs">Breakeven after {breakEvenPips} pips</Label>
                <Switch checked={breakEvenEnabled} onCheckedChange={setBreakEvenEnabled} />
              </div>
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
