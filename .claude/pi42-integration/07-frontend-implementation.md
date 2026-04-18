# Pi42 Frontend Implementation Plan

## Overview

The frontend requires significant modifications to support crypto futures trading. This document details all UI changes, new components, and modifications needed for Pi42 integration.

## Key UI Differences

### Stock Trading UI vs Crypto Futures UI

| Component | Stock Trading | Crypto Futures (Pi42) |
|-----------|--------------|----------------------|
| **Exchange Selector** | NSE, BSE, NFO, BFO | Not needed (always Pi42) |
| **Product Type** | MIS, NRML, CNC | Margin Mode: ISOLATED/CROSS |
| **Leverage** | Fixed by exchange | User-configurable slider (1x-25x) |
| **Margin Asset** | INR only | USDT, INR selector |
| **Position Display** | Quantity, Avg Price | + Liquidation Price, Unrealized PnL, ROE |
| **Market Hours** | 9:15 AM - 3:30 PM | 24/7 indicator |
| **Funding** | Not applicable | Funding rate display |
| **Order Types** | MARKET, LIMIT, SL, SL-M | + STOP_MARKET, STOP_LIMIT |

## New Components Required

### 1. Leverage Slider Component

**File:** `frontend/src/components/crypto/LeverageSlider.tsx`

```typescript
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
      // Calculate liquidation price
      const maintenanceMargin = 0.01; // 1%
      let liqPrice = 0;
      
      if (side === 'LONG') {
        liqPrice = entryPrice * (1 - 1/value + maintenanceMargin);
      } else {
        liqPrice = entryPrice * (1 + 1/value - maintenanceMargin);
      }
      
      setLiquidationPrice(liqPrice);
      
      // Calculate required margin
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
```

### 2. Margin Mode Toggle

**File:** `frontend/src/components/crypto/MarginModeToggle.tsx`

```typescript
import React from 'react';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { HelpCircle } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface MarginModeToggleProps {
  value: 'ISOLATED' | 'CROSS';
  onChange: (value: 'ISOLATED' | 'CROSS') => void;
}

export function MarginModeToggle({ value, onChange }: MarginModeToggleProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Label>Margin Mode</Label>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <HelpCircle className="h-4 w-4 text-muted-foreground" />
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p className="font-semibold mb-2">Isolated Margin:</p>
              <p className="text-sm mb-3">
                Risk is limited to the margin allocated to this position.
                Other positions are not affected if liquidated.
              </p>
              <p className="font-semibold mb-2">Cross Margin:</p>
              <p className="text-sm">
                All available balance is used as margin. Positions share
                margin and can support each other, but liquidation affects
                all positions.
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <RadioGroup value={value} onValueChange={onChange}>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="ISOLATED" id="isolated" />
          <Label htmlFor="isolated" className="cursor-pointer">
            Isolated
          </Label>
        </div>
        <div className="flex items-center space-x-2">
          <RadioGroupItem value="CROSS" id="cross" />
          <Label htmlFor="cross" className="cursor-pointer">
            Cross
          </Label>
        </div>
      </RadioGroup>
    </div>
  );
}
```

### 3. Margin Asset Selector

**File:** `frontend/src/components/crypto/MarginAssetSelector.tsx`

```typescript
import React from 'react';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface MarginAssetSelectorProps {
  value: string;
  onChange: (value: string) => void;
  availableAssets?: string[];
  balances?: Record<string, number>;
}

export function MarginAssetSelector({
  value,
  onChange,
  availableAssets = ['USDT', 'INR'],
  balances = {}
}: MarginAssetSelectorProps) {
  return (
    <div className="space-y-2">
      <Label>Margin Asset</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue placeholder="Select margin asset" />
        </SelectTrigger>
        <SelectContent>
          {availableAssets.map((asset) => (
            <SelectItem key={asset} value={asset}>
              <div className="flex items-center justify-between w-full">
                <span>{asset}</span>
                {balances[asset] !== undefined && (
                  <span className="text-sm text-muted-foreground ml-4">
                    Balance: {balances[asset].toFixed(2)}
                  </span>
                )}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
```

### 4. Position Card with Crypto Features

**File:** `frontend/src/components/crypto/CryptoPositionCard.tsx`

```typescript
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';

interface CryptoPositionCardProps {
  position: {
    symbol: string;
    side: 'LONG' | 'SHORT';
    quantity: number;
    entryPrice: number;
    markPrice: number;
    liquidationPrice: number;
    unrealizedPnl: number;
    margin: number;
    leverage: number;
    marginMode: string;
    roe: number;
  };
  onAddMargin?: () => void;
  onReduceMargin?: () => void;
  onClose?: () => void;
}

export function CryptoPositionCard({
  position,
  onAddMargin,
  onReduceMargin,
  onClose
}: CryptoPositionCardProps) {
  const isProfitable = position.unrealizedPnl >= 0;
  const liquidationRisk = calculateLiquidationRisk(
    position.markPrice,
    position.liquidationPrice,
    position.side
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{position.symbol}</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={position.side === 'LONG' ? 'default' : 'destructive'}>
              {position.side}
            </Badge>
            <Badge variant="outline">{position.leverage}x</Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Position Details */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Quantity:</span>
            <span className="ml-2 font-medium">{position.quantity}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Entry Price:</span>
            <span className="ml-2 font-medium">${position.entryPrice}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Mark Price:</span>
            <span className="ml-2 font-medium">${position.markPrice}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Margin:</span>
            <span className="ml-2 font-medium">${position.margin}</span>
          </div>
        </div>

        {/* PnL Display */}
        <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
          <div>
            <div className="text-sm text-muted-foreground">Unrealized PnL</div>
            <div className={`text-2xl font-bold flex items-center gap-2 ${
              isProfitable ? 'text-green-600' : 'text-red-600'
            }`}>
              {isProfitable ? <TrendingUp /> : <TrendingDown />}
              ${Math.abs(position.unrealizedPnl).toFixed(2)}
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-muted-foreground">ROE</div>
            <div className={`text-xl font-bold ${
              isProfitable ? 'text-green-600' : 'text-red-600'
            }`}>
              {position.roe > 0 ? '+' : ''}{position.roe}%
            </div>
          </div>
        </div>

        {/* Liquidation Warning */}
        <div className={`p-3 rounded-lg ${
          liquidationRisk === 'high' ? 'bg-red-100 dark:bg-red-900/20' :
          liquidationRisk === 'medium' ? 'bg-yellow-100 dark:bg-yellow-900/20' :
          'bg-green-100 dark:bg-green-900/20'
        }`}>
          <div className="flex items-center gap-2 mb-1">
            {liquidationRisk !== 'low' && <AlertTriangle className="h-4 w-4" />}
            <span className="text-sm font-medium">Liquidation Price</span>
          </div>
          <div className="text-lg font-bold">${position.liquidationPrice}</div>
          <div className="text-xs text-muted-foreground mt-1">
            Risk: {liquidationRisk.toUpperCase()}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onAddMargin} className="flex-1">
            Add Margin
          </Button>
          <Button variant="outline" size="sm" onClick={onReduceMargin} className="flex-1">
            Reduce Margin
          </Button>
          <Button variant="destructive" size="sm" onClick={onClose} className="flex-1">
            Close
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function calculateLiquidationRisk(
  markPrice: number,
  liquidationPrice: number,
  side: 'LONG' | 'SHORT'
): 'low' | 'medium' | 'high' {
  const distance = side === 'LONG'
    ? ((markPrice - liquidationPrice) / markPrice) * 100
    : ((liquidationPrice - markPrice) / markPrice) * 100;

  if (distance > 20) return 'low';
  if (distance > 10) return 'medium';
  return 'high';
}
```

### 5. Funding Rate Display

**File:** `frontend/src/components/crypto/FundingRateDisplay.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Clock, TrendingUp, TrendingDown } from 'lucide-react';

interface FundingRateDisplayProps {
  symbol: string;
  fundingRate: number;
  nextFundingTime: number;
}

export function FundingRateDisplay({
  symbol,
  fundingRate,
  nextFundingTime
}: FundingRateDisplayProps) {
  const [timeRemaining, setTimeRemaining] = useState<string>('');

  useEffect(() => {
    const updateTimer = () => {
      const now = Date.now();
      const diff = nextFundingTime - now;

      if (diff <= 0) {
        setTimeRemaining('Funding in progress...');
        return;
      }

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      setTimeRemaining(`${hours}h ${minutes}m ${seconds}s`);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [nextFundingTime]);

  const isPositive = fundingRate >= 0;
  const ratePercentage = (fundingRate * 100).toFixed(4);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Funding Rate - {symbol}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-2xl font-bold flex items-center gap-2">
              {isPositive ? (
                <TrendingUp className="h-5 w-5 text-green-600" />
              ) : (
                <TrendingDown className="h-5 w-5 text-red-600" />
              )}
              <span className={isPositive ? 'text-green-600' : 'text-red-600'}>
                {ratePercentage}%
              </span>
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {isPositive ? 'Longs pay Shorts' : 'Shorts pay Longs'}
            </div>
          </div>
          <div className="text-right">
            <Badge variant="outline">{timeRemaining}</Badge>
            <div className="text-xs text-muted-foreground mt-1">
              Next funding
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### 6. Split TP/SL Component

**File:** `frontend/src/components/crypto/SplitTPSL.tsx`

```typescript
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus, Trash2 } from 'lucide-react';

interface TPSLLevel {
  price: number;
  quantity: number;
}

interface SplitTPSLProps {
  symbol: string;
  positionQuantity: number;
  onSubmit: (tpLevels: TPSLLevel[], slLevels: TPSLLevel[]) => void;
}

export function SplitTPSL({ symbol, positionQuantity, onSubmit }: SplitTPSLProps) {
  const [tpLevels, setTpLevels] = useState<TPSLLevel[]>([
    { price: 0, quantity: 0 }
  ]);
  const [slLevels, setSlLevels] = useState<TPSLLevel[]>([
    { price: 0, quantity: 0 }
  ]);

  const addTPLevel = () => {
    setTpLevels([...tpLevels, { price: 0, quantity: 0 }]);
  };

  const removeTPLevel = (index: number) => {
    setTpLevels(tpLevels.filter((_, i) => i !== index));
  };

  const updateTPLevel = (index: number, field: 'price' | 'quantity', value: number) => {
    const updated = [...tpLevels];
    updated[index][field] = value;
    setTpLevels(updated);
  };

  const addSLLevel = () => {
    setSlLevels([...slLevels, { price: 0, quantity: 0 }]);
  };

  const removeSLLevel = (index: number) => {
    setSlLevels(slLevels.filter((_, i) => i !== index));
  };

  const updateSLLevel = (index: number, field: 'price' | 'quantity', value: number) => {
    const updated = [...slLevels];
    updated[index][field] = value;
    setSlLevels(updated);
  };

  const handleSubmit = () => {
    onSubmit(tpLevels, slLevels);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Split Take Profit / Stop Loss</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Take Profit Levels */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <Label className="text-base">Take Profit Levels</Label>
            <Button variant="outline" size="sm" onClick={addTPLevel}>
              <Plus className="h-4 w-4 mr-1" />
              Add Level
            </Button>
          </div>
          <div className="space-y-3">
            {tpLevels.map((level, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="flex-1">
                  <Input
                    type="number"
                    placeholder="Price"
                    value={level.price || ''}
                    onChange={(e) => updateTPLevel(index, 'price', parseFloat(e.target.value))}
                  />
                </div>
                <div className="flex-1">
                  <Input
                    type="number"
                    placeholder="Quantity"
                    value={level.quantity || ''}
                    onChange={(e) => updateTPLevel(index, 'quantity', parseFloat(e.target.value))}
                  />
                </div>
                {tpLevels.length > 1 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeTPLevel(index)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Stop Loss Levels */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <Label className="text-base">Stop Loss Levels</Label>
            <Button variant="outline" size="sm" onClick={addSLLevel}>
              <Plus className="h-4 w-4 mr-1" />
              Add Level
            </Button>
          </div>
          <div className="space-y-3">
            {slLevels.map((level, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="flex-1">
                  <Input
                    type="number"
                    placeholder="Price"
                    value={level.price || ''}
                    onChange={(e) => updateSLLevel(index, 'price', parseFloat(e.target.value))}
                  />
                </div>
                <div className="flex-1">
                  <Input
                    type="number"
                    placeholder="Quantity"
                    value={level.quantity || ''}
                    onChange={(e) => updateSLLevel(index, 'quantity', parseFloat(e.target.value))}
                  />
                </div>
                {slLevels.length > 1 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeSLLevel(index)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </div>

        <Button onClick={handleSubmit} className="w-full">
          Set Split TP/SL
        </Button>
      </CardContent>
    </Card>
  );
}
```

## Modified Components

### 1. Order Form Modifications

**File:** `frontend/src/components/OrderForm.tsx`

```typescript
// Add crypto-specific fields
import { LeverageSlider } from './crypto/LeverageSlider';
import { MarginModeToggle } from './crypto/MarginModeToggle';
import { MarginAssetSelector } from './crypto/MarginAssetSelector';

// Inside OrderForm component
const [leverage, setLeverage] = useState(1);
const [marginMode, setMarginMode] = useState<'ISOLATED' | 'CROSS'>('ISOLATED');
const [marginAsset, setMarginAsset] = useState('USDT');

// Detect if current broker is crypto
const isCrypto = currentBroker === 'pi42';

// Render crypto-specific fields
{isCrypto && (
  <>
    <LeverageSlider
      value={leverage}
      onChange={setLeverage}
      entryPrice={parseFloat(price)}
      quantity={parseFloat(quantity)}
      side={action === 'BUY' ? 'LONG' : 'SHORT'}
    />
    
    <MarginModeToggle
      value={marginMode}
      onChange={setMarginMode}
    />
    
    <MarginAssetSelector
      value={marginAsset}
      onChange={setMarginAsset}
    />
  </>
)}
```

### 2. Position Book Modifications

Replace standard position cards with `CryptoPositionCard` when broker is Pi42.

### 3. Dashboard Modifications

Add crypto-specific widgets:
- Funding rate display
- 24/7 market status indicator
- Liquidation risk overview
- Total unrealized PnL across all positions

## State Management

### Zustand Store for Crypto

**File:** `frontend/src/stores/cryptoStore.ts`

```typescript
import { create } from 'zustand';

interface CryptoState {
  fundingRates: Record<string, number>;
  liquidationAlerts: Array<any>;
  marginCalls: Array<any>;
  setFundingRate: (symbol: string, rate: number) => void;
  addLiquidationAlert: (alert: any) => void;
  addMarginCall: (call: any) => void;
  clearAlerts: () => void;
}

export const useCryptoStore = create<CryptoState>((set) => ({
  fundingRates: {},
  liquidationAlerts: [],
  marginCalls: [],
  
  setFundingRate: (symbol, rate) =>
    set((state) => ({
      fundingRates: { ...state.fundingRates, [symbol]: rate }
    })),
  
  addLiquidationAlert: (alert) =>
    set((state) => ({
      liquidationAlerts: [...state.liquidationAlerts, alert]
    })),
  
  addMarginCall: (call) =>
    set((state) => ({
      marginCalls: [...state.marginCalls, call]
    })),
  
  clearAlerts: () =>
    set({ liquidationAlerts: [], marginCalls: [] })
}));
```

## Real-Time Updates

### Socket.IO Event Handlers

**File:** `frontend/src/hooks/useCryptoWebSocket.ts`

```typescript
import { useEffect } from 'react';
import { socket } from '@/lib/socket';
import { useCryptoStore } from '@/stores/cryptoStore';
import { toast } from 'sonner';

export function useCryptoWebSocket() {
  const { setFundingRate, addLiquidationAlert, addMarginCall } = useCryptoStore();

  useEffect(() => {
    // Position updates
    socket.on('position_update', (data) => {
      console.log('Position update:', data);
      // Update position in state
    });

    // Funding fee
    socket.on('funding_fee', (data) => {
      setFundingRate(data.symbol, data.funding_rate);
      toast.info(`Funding fee: ${data.funding_fee} ${data.symbol}`);
    });

    // Margin call alert
    socket.on('margin_call_alert', (data) => {
      addMarginCall(data);
      toast.warning(`Margin call: ${data.data.symbol}`, {
        description: 'Add margin to avoid liquidation'
      });
    });

    // Liquidation alert
    socket.on('liquidation_alert', (data) => {
      addLiquidationAlert(data);
      toast.error(`LIQUIDATION WARNING: ${data.data.symbol}`, {
        description: 'Position at risk of liquidation!',
        duration: 10000
      });
    });

    return () => {
      socket.off('position_update');
      socket.off('funding_fee');
      socket.off('margin_call_alert');
      socket.off('liquidation_alert');
    };
  }, []);
}
```

## Testing

### Component Tests

```typescript
// LeverageSlider.test.tsx
import { render, screen } from '@testing-library/react';
import { LeverageSlider } from './LeverageSlider';

test('renders leverage slider', () => {
  render(<LeverageSlider value={10} onChange={() => {}} />);
  expect(screen.getByText('10x')).toBeInTheDocument();
});

test('calculates liquidation price correctly', () => {
  render(
    <LeverageSlider
      value={10}
      onChange={() => {}}
      entryPrice={50000}
      quantity={0.5}
      side="LONG"
    />
  );
  // Assert liquidation price is displayed
});
```

## Next Steps

1. Create all new crypto components
2. Modify existing components for crypto support
3. Implement state management
4. Add WebSocket event handlers
5. Test all components
6. Add responsive design
7. Document component usage
