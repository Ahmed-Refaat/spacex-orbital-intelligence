import { lazy, Suspense } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useStore } from '@/stores/useStore'

// Lazy load heavy components for code splitting
const Globe = lazy(() => import('@/components/Globe').then(m => ({ default: m.Globe })))
const Sidebar = lazy(() => import('@/components/Sidebar').then(m => ({ default: m.Sidebar })))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 2,
    },
  },
})

function AppContent() {
  // Initialize WebSocket connection
  useWebSocket()
  const { wsConnected } = useStore()

  return (
    <div className="h-screen w-screen overflow-hidden bg-spacex-dark">
      {/* Header - z-10 so sidebar (z-20) covers it on mobile */}
      <header className="absolute top-0 left-0 right-0 z-10 pointer-events-none">
        <div className="p-4 pb-8 flex justify-between items-center">
          <div className="pointer-events-auto">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold leading-tight">SpaceX Orbital Intelligence</h1>
              <span className="px-1.5 py-0.5 text-[9px] font-bold bg-yellow-500/20 text-yellow-400 rounded uppercase tracking-wider">
                Demo
              </span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className={`w-2 h-2 rounded-full ${
                wsConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
              }`} />
              <span className={`text-xs ${wsConnected ? 'text-green-400' : 'text-red-400'}`}>
                {wsConnected ? 'Live' : 'Connecting...'}
              </span>
              <span className="text-xs text-gray-500">•</span>
              <p className="text-xs text-gray-400">Real-time Starlink Constellation Tracking</p>
            </div>
          </div>
        </div>
      </header>

      {/* 3D Globe */}
      <main className="absolute inset-0">
        <ErrorBoundary>
          <Suspense fallback={
            <div className="flex items-center justify-center h-full">
              <div className="text-white text-sm">Loading 3D Globe...</div>
            </div>
          }>
            <Globe />
          </Suspense>
        </ErrorBoundary>
      </main>

      {/* Sidebar */}
      <Suspense fallback={
        <div className="absolute top-0 right-0 w-80 h-full bg-spacex-dark/95 backdrop-blur-sm border-l border-spacex-border flex items-center justify-center">
          <div className="text-white text-sm">Loading controls...</div>
        </div>
      }>
        <Sidebar />
      </Suspense>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  )
}
