import { create } from 'zustand';
import type { Position, Trade } from '@/types';

interface TradingState {
  positions: Position[];
  trades: Trade[];
  selectedSymbol: string;
  setPositions: (positions: Position[]) => void;
  setTrades: (trades: Trade[]) => void;
  setSelectedSymbol: (symbol: string) => void;
  addPosition: (position: Position) => void;
  removePosition: (positionId: string) => void;
  updatePosition: (positionId: string, updates: Partial<Position>) => void;
}

export const useTradingStore = create<TradingState>((set) => ({
  positions: [],
  trades: [],
  selectedSymbol: 'EURUSD',
  
  setPositions: (positions) => set({ positions }),
  setTrades: (trades) => set({ trades }),
  setSelectedSymbol: (selectedSymbol) => set({ selectedSymbol }),
  
  addPosition: (position) =>
    set((state) => ({
      positions: [...state.positions, position],
    })),
  
  removePosition: (positionId) =>
    set((state) => ({
      positions: state.positions.filter((p) => p.id !== positionId),
    })),
  
  updatePosition: (positionId, updates) =>
    set((state) => ({
      positions: state.positions.map((p) =>
        p.id === positionId ? { ...p, ...updates } : p
      ),
    })),
}));
