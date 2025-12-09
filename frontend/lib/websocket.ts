// WebSocket stub - disabled for now
// Backend uses native FastAPI WebSocket at /api/websocket/connector
// Frontend uses Socket.io which is incompatible
// TODO: Either migrate backend to Socket.io or frontend to native WebSocket

let isConnected = false;

export function getSocket(): any {
  return {
    on: () => { },
    off: () => { },
    emit: () => { },
    connect: () => {
      console.log('WebSocket disabled - using REST API fallback');
    },
    disconnect: () => { },
    connected: false,
    auth: {},
  };
}

export function connectSocket(token?: string) {
  // Disabled - WebSocket not compatible between Socket.io and FastAPI
  console.log('WebSocket disabled - real-time features will use polling');
  isConnected = false;
  return getSocket();
}

export function disconnectSocket() {
  isConnected = false;
}

export function isSocketConnected(): boolean {
  return isConnected;
}

// Event types (kept for type compatibility)
export interface PriceUpdate {
  symbol: string;
  bid: number;
  ask: number;
  timestamp: string;
}

export interface PositionUpdate {
  id: string;
  symbol: string;
  profit: number;
  current_price: number;
}

export interface TradeNotification {
  type: 'order_filled' | 'position_closed' | 'stop_loss' | 'take_profit';
  message: string;
  data: any;
}
