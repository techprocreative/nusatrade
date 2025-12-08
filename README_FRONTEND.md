# Forex AI Trading Platform - Frontend

**Status**: ✅ **PRODUCTION READY - 100% COMPLETE**

Modern, responsive frontend for AI-powered Forex trading platform built with Next.js 14, TypeScript, and TailwindCSS.

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Environment Setup

Create `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### Development

```bash
npm run dev
# Visit http://localhost:3000
```

### Production Build

```bash
npm run build
npm start
```

---

## ✨ Features

### 1. Authentication System
- ✅ Login/Register with validation
- ✅ JWT token management
- ✅ Protected routes
- ✅ Auto logout on expiry

### 2. Trading Platform
- ✅ Real-time price updates (WebSocket)
- ✅ Place/close orders
- ✅ Position management
- ✅ Trade history
- ✅ Profit/loss tracking

### 3. ML Bots
- ✅ Create/train ML models
- ✅ Toggle activation
- ✅ Performance metrics
- ✅ Model configuration

### 4. AI Supervisor
- ✅ Real-time chat interface
- ✅ Market analysis
- ✅ Trading recommendations
- ✅ Quick actions

### 5. Backtesting
- ✅ Strategy testing
- ✅ Historical analysis
- ✅ Performance metrics
- ✅ Trade breakdown

### 6. Mobile Responsive
- ✅ Responsive sidebar
- ✅ Mobile drawer menu
- ✅ Touch-optimized UI
- ✅ Responsive tables

---

## 🏗️ Tech Stack

### Core
- **Next.js 14** - React framework
- **TypeScript** - Type safety (strict mode)
- **TailwindCSS** - Styling
- **shadcn/ui** - Component library

### State Management
- **React Query** - Server state
- **Zustand** - Client state
- **Context API** - Auth state

### Real-time
- **Socket.io Client** - WebSocket
- **Axios** - HTTP client

### UI/UX
- **Framer Motion** - Animations (via shadcn)
- **Lucide React** - Icons
- **Sonner** - Toast notifications

---

## 📁 Project Structure

```
frontend/
├── app/                      # Next.js app directory
│   ├── (auth)/              # Auth pages
│   │   └── login/
│   ├── (dashboard)/         # Dashboard pages
│   │   ├── layout.tsx       # Sidebar + WebSocket
│   │   ├── page.tsx         # Overview
│   │   ├── trading/
│   │   ├── bots/
│   │   ├── ai-supervisor/
│   │   ├── backtest/
│   │   ├── connections/
│   │   └── settings/
│   └── layout.tsx           # Root layout
├── components/
│   ├── ui/                  # shadcn components
│   ├── loading/             # Loading skeletons
│   ├── error/               # Error boundaries
│   └── ProtectedRoute.tsx
├── hooks/
│   ├── api/                 # API hooks
│   │   ├── useTrading.ts
│   │   ├── useBots.ts
│   │   ├── useBacktest.ts
│   │   ├── useAI.ts
│   │   └── index.ts
│   ├── useWebSocket.ts      # WebSocket hooks
│   └── use-toast.ts
├── lib/
│   ├── api-client.ts        # Axios setup
│   ├── react-query.tsx      # React Query provider
│   ├── websocket.ts         # Socket.io setup
│   └── utils.ts
├── contexts/
│   └── AuthContext.tsx      # Auth provider
├── stores/
│   ├── useAuthStore.ts      # Auth state
│   └── useTradingStore.ts   # Trading state
├── types/
│   └── index.ts             # TypeScript types
└── public/                  # Static assets
```

---

## 🎨 Design System

### Colors
- **Primary**: Blue (`hsl(222, 84%, 55%)`)
- **Success**: Green (`#10b981`)
- **Error**: Red (`#ef4444`)
- **Dark**: Full dark theme

### Typography
- **Font**: Inter
- **Headings**: Bold, 2xl-4xl
- **Body**: Regular, sm-base

### Components
- Consistent spacing (4px base)
- Rounded corners (lg = 8px)
- Shadows for depth
- Smooth transitions

---

## 🔌 API Integration

### API Hooks

All API calls use React Query hooks with:
- ✅ Automatic caching (1min stale time)
- ✅ Loading & error states
- ✅ Toast notifications
- ✅ Auto retry on failure

**Example**:
```typescript
import { usePositions } from '@/hooks/api';

const { data: positions, isLoading } = usePositions();
```

### Available Hooks

**Trading**:
- `usePositions()` - Get open positions
- `useTrades()` - Get trade history
- `usePlaceOrder()` - Place new order
- `useClosePosition()` - Close position

**ML Bots**:
- `useMLModels()` - Get all models
- `useCreateMLModel()` - Create model
- `useToggleMLModel()` - Activate/deactivate
- `useTrainMLModel()` - Train model
- `useDeleteMLModel()` - Delete model

**Backtesting**:
- `useStrategies()` - Get strategies
- `useRunBacktest()` - Run backtest
- `useBacktestResult()` - Get results

**AI Supervisor**:
- `useSendMessage()` - Send chat message
- `useGetDailyAnalysis()` - Get daily analysis
- `useGetSymbolAnalysis()` - Analyze symbol

---

## 🔄 WebSocket Integration

### Real-time Updates

**Connection**:
```typescript
import { useWebSocketConnection } from '@/hooks/useWebSocket';

const { isConnected } = useWebSocketConnection();
```

**Price Updates**:
```typescript
import { usePriceUpdates } from '@/hooks/useWebSocket';

const prices = usePriceUpdates('EURUSD');
// prices['EURUSD'] = { bid, ask, timestamp }
```

**Position Updates**:
```typescript
import { usePositionUpdates } from '@/hooks/useWebSocket';

const positionUpdates = usePositionUpdates();
// Real-time profit/loss updates
```

**Trade Notifications**:
```typescript
import { useTradeNotifications } from '@/hooks/useWebSocket';

useTradeNotifications(); // Auto-shows toasts
```

---

## 🎯 Code Quality

- ✅ **TypeScript Strict Mode** - Full type safety
- ✅ **ESLint** - Code linting
- ✅ **Prettier** - Code formatting
- ✅ **No console errors** - Clean production build
- ✅ **Zero build warnings** - Optimized code

---

## 📱 Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers

---

## 🐛 Troubleshooting

### Build fails
```bash
# Clear cache
rm -rf .next node_modules
npm install
npm run build
```

### WebSocket not connecting
- Check `NEXT_PUBLIC_WS_URL` in `.env.local`
- Ensure backend WebSocket server is running
- Check browser console for errors

### API calls failing
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Ensure backend API is running
- Check network tab for 401/403 errors

---

## 📄 License

See root LICENSE file.

---

## 🤝 Contributing

This is a production system. Contact maintainers before contributing.

---

## 📚 Documentation

- [PROGRESS_REPORT.md](./PROGRESS_REPORT.md) - Development progress
- [COMPLETION_REPORT.md](./COMPLETION_REPORT.md) - Feature documentation
- [.env.example](./.env.example) - Environment variables

---

**Built with ❤️ using Next.js, TypeScript, and TailwindCSS**

**Status**: ✅ Production Ready | 🚀 Ready for Real Money Trading
