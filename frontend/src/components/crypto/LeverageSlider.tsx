import React, { useState, useEffect } from 'react';
import { Slider } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle } from 'lucide-react';

interface LeverageSliderProps {
  value: number;
  onChange: (value: number) => void;
  maxLeverage?: number;
  entryPrice?: number;
  quantity?: number;
  side?: 'LONG' | 'SHORT';
}

export function LeverageSlider({
  value,
  onChange,
  maxLeverage = 25,
  entryPrice,
  quantity,
  side
}: LeverageSliderProps) {
  const [liquidationPrice, setLiquidationPrice] = useState<number>(0);
  const [requiredMargin, setRequiredMargin] = useState<number>(0);

  useEffect(() => {
    if (entryPrice && quantity && value > 0) {
      const maintenanceMargin = 0.01;
      let liqPrice = 0;

      if (side === 'LONG') {
        liqPrice = entryPrice * (1 - 1/value + maintenanceMargin);
      } else {
        liqPrice = entryPrice * (1 + 1/value - maintenanceMargin);
      }

      setLiquidationPrice(liqPrice);

      const positionValue = quantity * entryPrice;
      const margin = positionValue / value;
      setRequiredMargin(margin);
    }
  }, [value, entryPrice, quantity, side]);

  const getRiskLevel = (leverage: number): string => {
    if (leverage <= 5) return 'Low';
    if (leverage <= 10) return 'Medium';
    if (leverage <= 15) return 'High';
    return 'Very High';
  };

  const getRiskColor = (leverage: number): string => {
    if (leverage <= 5) return 'text-green-600';
    if (leverage <= 10) return 'text-yellow-600';
    if (leverage <= 15) return 'text-orange-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label>Leverage</Label>
        <div className="flex items-center gap-2">
          <span className="text-2xl font-bold">{value}x</span>
          <span className={`text-sm ${getRiskColor(value)}`}>
            {getRiskLevel(value)} Risk
          </span>
        </div>
      </div>

      <Slider
        value={[value]}
        onValueChange={(values) => onChange(values[0])}
        min={1}
        max={maxLeverage}
        step={1}
        className="w-full"
      />

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-muted-foreground">Required Margin:</span>
          <span className="ml-2 font-medium">
            ${requiredMargin.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground">Liquidation Price:</span>
          <span className="ml-2 font-medium">
            ${liquidationPrice.toFixed(2)}
          </span>
        </div>
      </div>

      {value > 10 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            High leverage increases liquidation risk. Use with caution.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
