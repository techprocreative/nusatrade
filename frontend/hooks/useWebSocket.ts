import { useEffect, useState, useCallback } from 'react';
import {
  wsClient,
  ConnectionStatus,
  PositionUpdate,
  TradeResult,
  AccountUpdate,
} from '@/lib/websocket';
import { useToast } from '@/hooks/use-toast';

/**
 * Hook for managing WebSocket connection state
 */
export function useWebSocketConnection() {
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const handleConnect = () => setIsConnected(true);
    const handleDisconnect = () => setIsConnected(false);

    wsClient.on('connect', handleConnect);
    wsClient.on('disconnect', handleDisconnect);

    // Check initial state
    setIsConnected(wsClient.isConnected);

    return () => {
      wsClient.off('connect', handleConnect);
      wsClient.off('disconnect', handleDisconnect);
    };
  }, []);

  const connect = useCallback((token: string) => {
    wsClient.connect(token);
  }, []);

  const disconnect = useCallback(() => {
    wsClient.disconnect();
  }, []);

  return { isConnected, connect, disconnect };
}

/**
 * Hook for receiving connection status updates
 */
export function useConnectionStatus() {
  const [connections, setConnections] = useState<ConnectionStatus[]>([]);

  useEffect(() => {
    const handleConnectionsStatus = (data: { connections: ConnectionStatus[] }) => {
      setConnections(data.connections || []);
    };

    const handleMT5Status = (data: any) => {
      setConnections((prev) => {
        const idx = prev.findIndex((c) => c.connection_id === data.connection_id);
        if (idx >= 0) {
          const updated = [...prev];
          updated[idx] = {
            ...updated[idx],
            mt5_connected: data.connected,
            broker_name: data.broker_name,
          };
          return updated;
        }
        return prev;
      });
    };

    const handleDisconnected = (data: { connection_id: string }) => {
      setConnections((prev) =>
        prev.map((c) =>
          c.connection_id === data.connection_id ? { ...c, mt5_connected: false } : c
        )
      );
    };

    wsClient.on('CONNECTIONS_STATUS', handleConnectionsStatus);
    wsClient.on('MT5_STATUS_UPDATE', handleMT5Status);
    wsClient.on('CONNECTOR_DISCONNECTED', handleDisconnected);

    return () => {
      wsClient.off('CONNECTIONS_STATUS', handleConnectionsStatus);
      wsClient.off('MT5_STATUS_UPDATE', handleMT5Status);
      wsClient.off('CONNECTOR_DISCONNECTED', handleDisconnected);
    };
  }, []);

  return connections;
}

/**
 * Hook for receiving position updates
 */
export function usePositionUpdates() {
  const [positions, setPositions] = useState<Record<string, PositionUpdate>>({});

  useEffect(() => {
    const handlePositionUpdate = (data: PositionUpdate) => {
      setPositions((prev) => ({
        ...prev,
        [data.id]: data,
      }));
    };

    wsClient.on('POSITION_UPDATE', handlePositionUpdate);

    return () => {
      wsClient.off('POSITION_UPDATE', handlePositionUpdate);
    };
  }, []);

  return positions;
}

/**
 * Hook for receiving account updates
 */
export function useAccountUpdates() {
  const [accounts, setAccounts] = useState<Record<string, AccountUpdate>>({});

  useEffect(() => {
    const handleAccountUpdate = (data: AccountUpdate) => {
      setAccounts((prev) => ({
        ...prev,
        [data.connection_id]: data,
      }));
    };

    wsClient.on('ACCOUNT_UPDATE', handleAccountUpdate);

    return () => {
      wsClient.off('ACCOUNT_UPDATE', handleAccountUpdate);
    };
  }, []);

  return accounts;
}

/**
 * Hook for receiving trade notifications with toast display
 */
export function useTradeNotifications() {
  const { toast } = useToast();

  useEffect(() => {
    const handleTradeResult = (data: TradeResult) => {
      if (data.success) {
        toast({
          title: 'Trade Executed',
          description: data.message || `Order ${data.order_id} executed successfully`,
        });
      } else {
        toast({
          variant: 'destructive',
          title: 'Trade Failed',
          description: data.error || 'Failed to execute trade',
        });
      }
    };

    const handleConnectorError = (data: { error: string; connection_id: string }) => {
      toast({
        variant: 'destructive',
        title: 'Connector Error',
        description: data.error,
      });
    };

    const handleConnectorDisconnected = (data: { connection_id: string }) => {
      toast({
        variant: 'destructive',
        title: 'Connector Disconnected',
        description: 'MT5 connector has disconnected',
      });
    };

    wsClient.on('TRADE_RESULT', handleTradeResult);
    wsClient.on('CONNECTOR_ERROR', handleConnectorError);
    wsClient.on('CONNECTOR_DISCONNECTED', handleConnectorDisconnected);

    return () => {
      wsClient.off('TRADE_RESULT', handleTradeResult);
      wsClient.off('CONNECTOR_ERROR', handleConnectorError);
      wsClient.off('CONNECTOR_DISCONNECTED', handleConnectorDisconnected);
    };
  }, [toast]);
}

/**
 * Hook for sending trade commands
 */
export function useTradingCommands() {
  const sendOrder = useCallback(
    (params: {
      connection_id: string;
      action: 'BUY' | 'SELL' | 'CLOSE';
      symbol: string;
      order_type?: string;
      lot_size?: number;
      stop_loss?: number;
      take_profit?: number;
    }) => {
      const command_id = `cmd_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      wsClient.sendTradeCommand({
        ...params,
        command_id,
      });
      return command_id;
    },
    []
  );

  return { sendOrder };
}

// Legacy exports for backward compatibility
export function usePriceUpdates(symbol?: string) {
  const [prices, setPrices] = useState<Record<string, any>>({});

  useEffect(() => {
    const handlePriceUpdate = (data: any) => {
      if (!symbol || data.symbol === symbol) {
        setPrices((prev) => ({
          ...prev,
          [data.symbol]: data,
        }));
      }
    };

    wsClient.on('PRICE_UPDATE', handlePriceUpdate);

    return () => {
      wsClient.off('PRICE_UPDATE', handlePriceUpdate);
    };
  }, [symbol]);

  return prices;
}
