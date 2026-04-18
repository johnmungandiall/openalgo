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
