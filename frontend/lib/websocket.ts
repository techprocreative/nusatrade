/**
 * Native WebSocket client for FastAPI backend
 * Handles connection to /connector/client endpoint for real-time dashboard updates
 */

type MessageHandler = (data: any) => void;

// Message types from backend
export type WebSocketMessageType =
  | 'CONNECTIONS_STATUS'
  | 'MT5_STATUS_UPDATE'
  | 'ACCOUNT_UPDATE'
  | 'TRADE_RESULT'
  | 'POSITION_UPDATE'
  | 'CONNECTOR_ERROR'
  | 'CONNECTOR_DISCONNECTED'
  | 'PONG'
  | 'ERROR';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  [key: string]: any;
}

export interface ConnectionStatus {
  connection_id: string;
  mt5_connected: boolean;
  broker_name: string | null;
}

export interface PositionUpdate {
  id: string;
  symbol: string;
  profit: number;
  current_price: number;
  connection_id: string;
}

export interface TradeResult {
  connection_id: string;
  success: boolean;
  order_id?: string;
  message?: string;
  error?: string;
}

export interface AccountUpdate {
  connection_id: string;
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private token: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: NodeJS.Timeout | null = null;
  private listeners: Map<string, Set<MessageHandler>> = new Map();
  private isIntentionalClose = false;

  /**
   * Connect to the WebSocket server
   */
  connect(token: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WS] Already connected');
      return;
    }

    this.token = token;
    this.isIntentionalClose = false;

    const wsProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const wsHost = apiUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');
    const wsUrl = `${wsProtocol}//${wsHost}/connector/client?token=${encodeURIComponent(token)}`;

    console.log('[WS] Connecting to:', wsUrl.replace(token, '***'));

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[WS] Connected');
        this.reconnectAttempts = 0;
        this.startPingInterval();
        this.emit('connect', {});
      };

      this.ws.onclose = (event) => {
        console.log('[WS] Disconnected:', event.code, event.reason);
        this.stopPingInterval();
        this.emit('disconnect', { code: event.code, reason: event.reason });

        if (!this.isIntentionalClose && this.token) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WS] Error:', error);
        this.emit('error', error);
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event);
      };
    } catch (error) {
      console.error('[WS] Connection error:', error);
      this.emit('error', error);
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.isIntentionalClose = true;
    this.stopPingInterval();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.token = null;
    this.reconnectAttempts = 0;
  }

  /**
   * Check if connected
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Send a message to the server
   */
  send(message: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('[WS] Cannot send - not connected');
    }
  }

  /**
   * Send a trade command to a connector
   */
  sendTradeCommand(params: {
    connection_id: string;
    command_id: string;
    action: 'BUY' | 'SELL' | 'CLOSE';
    symbol: string;
    order_type?: string;
    lot_size?: number;
    stop_loss?: number;
    take_profit?: number;
  }): void {
    this.send({
      type: 'SEND_TRADE_COMMAND',
      ...params,
    });
  }

  /**
   * Register an event listener
   */
  on(event: string, handler: MessageHandler): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);
  }

  /**
   * Remove an event listener
   */
  off(event: string, handler: MessageHandler): void {
    const handlers = this.listeners.get(event);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Emit an event to all listeners
   */
  private emit(event: string, data: any): void {
    const handlers = this.listeners.get(event);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data);
        } catch (error) {
          console.error(`[WS] Handler error for event ${event}:`, error);
        }
      });
    }
  }

  /**
   * Handle incoming messages
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      const { type, ...data } = message;

      // Emit the specific message type
      this.emit(type, data);

      // Also emit a generic 'message' event
      this.emit('message', message);
    } catch (error) {
      console.error('[WS] Failed to parse message:', error);
    }
  }

  /**
   * Start ping interval to keep connection alive
   */
  private startPingInterval(): void {
    this.stopPingInterval();
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'PING' });
      }
    }, 30000); // 30 seconds
  }

  /**
   * Stop ping interval
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Schedule a reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[WS] Max reconnect attempts reached');
      this.emit('reconnect_failed', {});
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    setTimeout(() => {
      if (this.token && !this.isIntentionalClose) {
        this.connect(this.token);
      }
    }, delay);
  }
}

// Singleton instance
export const wsClient = new WebSocketClient();

// Legacy exports for backward compatibility
export function connectSocket(token?: string): void {
  if (token) {
    wsClient.connect(token);
  } else if (typeof window !== 'undefined') {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      wsClient.connect(storedToken);
    }
  }
}

export function disconnectSocket(): void {
  wsClient.disconnect();
}

export function isSocketConnected(): boolean {
  return wsClient.isConnected;
}

// Legacy type exports
export interface PriceUpdate {
  symbol: string;
  bid: number;
  ask: number;
  timestamp: string;
}

export interface TradeNotification {
  type: 'order_filled' | 'position_closed' | 'stop_loss' | 'take_profit';
  message: string;
  data: any;
}
