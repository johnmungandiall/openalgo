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
