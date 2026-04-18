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
