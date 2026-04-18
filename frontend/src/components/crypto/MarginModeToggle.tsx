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
