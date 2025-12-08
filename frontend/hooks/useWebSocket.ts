import { useEffect, useState } from 'react';
import { getSocket, PriceUpdate, PositionUpdate, TradeNotification } from '@/lib/websocket';
import { useToast } from '@/hooks/use-toast';

export function useWebSocketConnection() {
  const [isConnected, setIsConnected] = useState(false);
  const socket = getSocket();

  useEffect(() => {
    const handleConnect = () => setIsConnected(true);
    const handleDisconnect = () => setIsConnected(false);

    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);

    if (socket.connected) {
      setIsConnected(true);
    }

    return () => {
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
    };
  }, [socket]);

  return { isConnected, socket };
}

export function usePriceUpdates(symbol?: string) {
  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
  const socket = getSocket();

  useEffect(() => {
    const handlePriceUpdate = (data: PriceUpdate) => {
      if (!symbol || data.symbol === symbol) {
        setPrices((prev) => ({
          ...prev,
          [data.symbol]: data,
        }));
      }
    };

    socket.on('price_update', handlePriceUpdate);

    // Subscribe to symbols
    if (symbol) {
      socket.emit('subscribe_prices', { symbols: [symbol] });
    }

    return () => {
      socket.off('price_update', handlePriceUpdate);
      if (symbol) {
        socket.emit('unsubscribe_prices', { symbols: [symbol] });
      }
    };
  }, [socket, symbol]);

  return prices;
}

export function usePositionUpdates() {
  const [positions, setPositions] = useState<Record<string, PositionUpdate>>({});
  const socket = getSocket();

  useEffect(() => {
    const handlePositionUpdate = (data: PositionUpdate) => {
      setPositions((prev) => ({
        ...prev,
        [data.id]: data,
      }));
    };

    socket.on('position_update', handlePositionUpdate);

    return () => {
      socket.off('position_update', handlePositionUpdate);
    };
  }, [socket]);

  return positions;
}

export function useTradeNotifications() {
  const { toast } = useToast();
  const socket = getSocket();

  useEffect(() => {
    const handleNotification = (data: TradeNotification) => {
      toast({
        title: data.type.replace(/_/g, ' ').toUpperCase(),
        description: data.message,
        variant: data.type === 'stop_loss' ? 'destructive' : 'default',
      });
    };

    socket.on('trade_notification', handleNotification);

    return () => {
      socket.off('trade_notification', handleNotification);
    };
  }, [socket, toast]);
}
