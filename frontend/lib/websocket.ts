import { io, Socket } from 'socket.io-client';

let socket: Socket | null = null;

export function getSocket(): Socket {
  if (!socket) {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'http://localhost:8000';
    
    socket = io(wsUrl, {
      autoConnect: false,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      transports: ['websocket', 'polling'],
    });

    socket.on('connect', () => {
      console.log('WebSocket connected');
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });

    socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
    });
  }

  return socket;
}

export function connectSocket(token?: string) {
  const socket = getSocket();
  
  if (token) {
    socket.auth = { token };
  }
  
  socket.connect();
  return socket;
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}

// Event types
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
