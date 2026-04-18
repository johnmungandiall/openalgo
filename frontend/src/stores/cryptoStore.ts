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
