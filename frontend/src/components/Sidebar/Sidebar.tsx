import { lazy, Suspense } from 'react'
import { useStore } from '@/stores/useStore'
import { SatellitesTab } from './SatellitesTab' // Eager load (always visible)
import { 
  Satellite, 
  BarChart3, 
  Rocket, 
  PlayCircle,
  Activity,
  Lightbulb,
  Zap,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'

// Lazy load tabs that aren't always visible
const AnalysisTab = lazy(() => import('./AnalysisTab').then(m => ({ default: m.AnalysisTab })))
const LaunchesTab = lazy(() => import('./LaunchesTab').then(m => ({ default: m.LaunchesTab })))
const SimulationTab = lazy(() => import('./SimulationTab').then(m => ({ default: m.SimulationTab })))
const OpsTab = lazy(() => import('./OpsTab').then(m => ({ default: m.OpsTab })))
const InsightsTab = lazy(() => import('./InsightsTab').then(m => ({ default: m.InsightsTab })))
const PerformanceTab = lazy(() => import('./PerformanceTab').then(m => ({ default: m.PerformanceTab })))

const tabs = [
  { id: 'satellites' as const, label: 'Satellites', icon: Satellite },
  { id: 'ops' as const, label: 'Ops', icon: Activity },
  { id: 'insights' as const, label: 'Insights', icon: Lightbulb },
  { id: 'analysis' as const, label: 'Analysis', icon: BarChart3 },
  { id: 'launches' as const, label: 'Launches', icon: Rocket },
  { id: 'simulation' as const, label: 'Sim', icon: PlayCircle },
  { id: 'performance' as const, label: 'Perf', icon: Zap },
]

export function Sidebar() {
  const { sidebarOpen, setSidebarOpen, activeTab, setActiveTab } = useStore()

  return (
    <div className={`
      fixed right-0 top-0 h-full z-20 flex transition-transform duration-300
      ${sidebarOpen ? 'translate-x-0' : 'translate-x-[calc(100%-48px)]'}
    `}>
      {/* Toggle button - larger on mobile */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="self-center -ml-10 w-10 h-16 md:w-8 md:h-14 md:-ml-8 bg-spacex-card hover:bg-spacex-border rounded-l-xl flex items-center justify-center transition"
      >
        {sidebarOpen ? <ChevronRight size={22} className="md:w-5 md:h-5" /> : <ChevronLeft size={22} className="md:w-5 md:h-5" />}
      </button>

      {/* Sidebar content */}
      <div className="w-80 md:w-96 h-full bg-spacex-card/95 backdrop-blur-lg border-l border-spacex-border flex flex-col">
        {/* Tabs */}
        <div className="flex border-b border-spacex-border">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex-1 py-3 px-2 flex flex-col items-center gap-1 transition
                ${activeTab === tab.id 
                  ? 'bg-spacex-accent/20 text-spacex-accent border-b-2 border-spacex-accent' 
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
                }
              `}
            >
              <tab.icon size={18} />
              <span className="text-xs">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-4">
          <Suspense fallback={<TabSkeleton />}>
            {activeTab === 'satellites' && <SatellitesTab />}
            {activeTab === 'ops' && <OpsTab />}
            {activeTab === 'insights' && <InsightsTab />}
            {activeTab === 'analysis' && <AnalysisTab />}
            {activeTab === 'launches' && <LaunchesTab />}
            {activeTab === 'simulation' && <SimulationTab />}
            {activeTab === 'performance' && <PerformanceTab />}
          </Suspense>
        </div>
      </div>
    </div>
  )
}

// Loading skeleton for lazy-loaded tabs
function TabSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-4 bg-gray-700 rounded w-3/4"></div>
      <div className="h-4 bg-gray-700 rounded w-1/2"></div>
      <div className="h-4 bg-gray-700 rounded w-5/6"></div>
      <div className="space-y-2 mt-6">
        <div className="h-20 bg-gray-700/50 rounded"></div>
        <div className="h-20 bg-gray-700/50 rounded"></div>
        <div className="h-20 bg-gray-700/50 rounded"></div>
      </div>
    </div>
  )
}
