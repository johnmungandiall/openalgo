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
