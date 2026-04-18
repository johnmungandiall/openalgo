import { useEffect } from 'react';
import { socket } from '@/lib/socket';
import { useCryptoStore } from '@/stores/cryptoStore';
import { toast } from 'sonner';

export function useCryptoWebSocket() {
  const { setFundingRate, addLiquidationAlert, addMarginCall } = useCryptoStore();

  useEffect(() => {
    socket.on('position_update', (data) => {
      console.log('Position update:', data);
    });

    socket.on('funding_fee', (data) => {
      setFundingRate(data.symbol, data.funding_rate);
      toast.info(`Funding fee: ${data.funding_fee} ${data.symbol}`);
    });

    socket.on('margin_call_alert', (data) => {
      addMarginCall(data);
      toast.warning(`Margin call: ${data.data.symbol}`, {
        description: 'Add margin to avoid liquidation'
      });
    });

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
  }, [setFundingRate, addLiquidationAlert, addMarginCall]);
}
