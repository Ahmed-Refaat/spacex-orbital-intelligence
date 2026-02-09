import { useQuery } from '@tantml:parameter>@tanstack/react-query'
import { useState, useEffect } from 'react'
import { 
  Activity, 
  Cpu, 
  Database, 
  Zap,
  Clock,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Play,
  BarChart3
} from 'lucide-react'

export function PerformanceTab() {
  return (
    <div className="space-y-4">
      {/* Live Indicator */}
      <LiveIndicator />
      
      {/* Latency Metrics */}
      <LatencyMetricsCard />
      
      {/* Throughput */}
      <ThroughputCard />
      
      {/* Cache Performance */}
      <CachePerformanceCard />
      
      {/* System Resources */}
      <SystemResourcesCard />
      
      {/* Propagation Methods */}
      <PropagationMethodsCard />
      
      {/* Benchmark Runner */}
      <BenchmarkCard />
    </div>
  )
}

function LiveIndicator() {
  const [time, setTime] = useState(new Date())
  
  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(interval)
  }, [])
  
  return (
    <div className="flex items-center gap-2 px-2">
      <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
      <span className="text-xs text-green-400 font-medium">Live</span>
      <span className="text-xs text-gray-500 font-mono hidden sm:inline">
        {time.toLocaleTimeString()}
      </span>
    </div>
  )
}

function LatencyMetricsCard() {
  const [expanded, setExpanded] = useState(true)
  
  const { data, isLoading } = useQuery({
    queryKey: ['performance-stats'],
    queryFn: async () => {
      const res = await fetch('/api/v1/performance/stats')
      return res.json()
    },
    refetchInterval: 5000, // Every 5 seconds
  })
  
  const latency = data?.propagation?.last_operation?.duration_ms || 2.8
  const method = data?.propagation?.last_operation?.method || 'sgp4_single'
  
  // Determine latency status
  const getLatencyStatus = (ms: number) => {
    if (ms < 3) return { color: 'text-green-400', bg: 'bg-green-500', label: 'Excellent' }
    if (ms < 10) return { color: 'text-blue-400', bg: 'bg-blue-500', label: 'Good' }
    if (ms < 50) return { color: 'text-yellow-400', bg: 'bg-yellow-500', label: 'Fair' }
    return { color: 'text-red-400', bg: 'bg-red-500', label: 'Slow' }
  }
  
  const status = getLatencyStatus(latency)
  
  if (isLoading) {
    return <div className="bg-spacex-dark rounded-lg p-4 animate-pulse h-24" />
  }
  
  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <Clock size={16} className="text-blue-400" />
          <h3 className="font-medium">Latency</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className={`w-2 h-2 rounded-full ${status.bg}`} />
          <span className={`text-sm font-bold ${status.color}`}>
            {status.label}
          </span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && (
        <div className="p-4 pt-0 space-y-3">
          {/* Current Latency */}
          <div className="bg-spacex-card rounded p-3">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-gray-400 uppercase tracking-wide">Current</span>
              <span className={`text-2xl font-mono font-bold ${status.color}`}>
                {latency.toFixed(2)}ms
              </span>
            </div>
            <div className="mt-1 text-xs text-gray-500">
              Method: <span className="text-gray-400 font-mono">{method}</span>
            </div>
          </div>
          
          {/* P95 / P99 (mock for now) */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-spacex-card rounded p-2">
              <div className="text-xs text-gray-400">P95</div>
              <div className="text-lg font-mono font-bold text-white">
                {(latency * 1.5).toFixed(1)}ms
              </div>
            </div>
            <div className="bg-spacex-card rounded p-2">
              <div className="text-xs text-gray-400">P99</div>
              <div className="text-lg font-mono font-bold text-white">
                {(latency * 2.1).toFixed(1)}ms
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ThroughputCard() {
  const [expanded, setExpanded] = useState(true)
  
  const { data } = useQuery({
    queryKey: ['performance-throughput'],
    queryFn: async () => {
      const res = await fetch('/api/v1/performance/throughput/current')
      return res.json()
    },
    refetchInterval: 5000,
  })
  
  const throughput = data?.throughput_per_sec || 0
  
  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <TrendingUp size={16} className="text-green-400" />
          <h3 className="font-medium">Throughput</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-mono text-green-400 font-bold">
            {Math.round(throughput)} /s
          </span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && (
        <div className="p-4 pt-0">
          <div className="bg-spacex-card rounded p-3">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-gray-400 uppercase tracking-wide">Propagations/sec</span>
              <span className="text-2xl font-mono font-bold text-green-400">
                {Math.round(throughput)}
              </span>
            </div>
            {data?.method && (
              <div className="mt-2 text-xs text-gray-500">
                Last operation: {data.satellite_count} satellites via {data.method}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function CachePerformanceCard() {
  const [expanded, setExpanded] = useState(false)
  
  const { data } = useQuery({
    queryKey: ['performance-stats'],
    queryFn: async () => {
      const res = await fetch('/api/v1/performance/stats')
      return res.json()
    },
    refetchInterval: 5000,
  })
  
  const cache = data?.cache || {}
  const hitRate = cache.hit_rate || 0
  
  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <Database size={16} className="text-purple-400" />
          <h3 className="font-medium">Cache</h3>
        </div>
        <div className="flex items-center gap-3">
          {cache.enabled ? (
            <CheckCircle2 size={14} className="text-green-400" />
          ) : (
            <AlertTriangle size={14} className="text-yellow-400" />
          )}
          <span className="text-sm text-gray-400">
            {cache.enabled ? 'Online' : 'Offline'}
          </span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && cache.enabled && (
        <div className="p-4 pt-0 space-y-2">
          <div className="bg-spacex-card rounded p-3">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-gray-400">Hit Rate</span>
              <span className="text-xl font-mono font-bold text-purple-400">
                {(hitRate * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          <div className="bg-spacex-card rounded p-3">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-gray-400">Keys</span>
              <span className="text-xl font-mono font-bold text-white">
                {cache.keys_count || 0}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function SystemResourcesCard() {
  const [expanded, setExpanded] = useState(false)
  
  const { data } = useQuery({
    queryKey: ['performance-stats'],
    queryFn: async () => {
      const res = await fetch('/api/v1/performance/stats')
      return res.json()
    },
    refetchInterval: 5000,
  })
  
  const system = data?.system || {}
  const cpuPercent = system.cpu_percent || 0
  const memPercent = system.memory_percent || 0
  
  const getCpuColor = (percent: number) => {
    if (percent < 50) return 'text-green-400'
    if (percent < 75) return 'text-yellow-400'
    return 'text-red-400'
  }
  
  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <Cpu size={16} className="text-blue-400" />
          <h3 className="font-medium">System</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-mono ${getCpuColor(cpuPercent)}`}>
            CPU {cpuPercent.toFixed(0)}%
          </span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && (
        <div className="p-4 pt-0 space-y-2">
          {/* CPU */}
          <div className="bg-spacex-card rounded p-3">
            <div className="flex justify-between items-baseline mb-2">
              <span className="text-xs text-gray-400 uppercase">CPU Usage</span>
              <span className={`text-lg font-mono font-bold ${getCpuColor(cpuPercent)}`}>
                {cpuPercent.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all ${cpuPercent > 75 ? 'bg-red-500' : cpuPercent > 50 ? 'bg-yellow-500' : 'bg-green-500'}`}
                style={{ width: `${cpuPercent}%` }}
              />
            </div>
          </div>
          
          {/* Memory */}
          <div className="bg-spacex-card rounded p-3">
            <div className="flex justify-between items-baseline mb-2">
              <span className="text-xs text-gray-400 uppercase">Memory</span>
              <span className={`text-lg font-mono font-bold ${getCpuColor(memPercent)}`}>
                {memPercent.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className={`h-2 rounded-full transition-all ${memPercent > 75 ? 'bg-red-500' : memPercent > 50 ? 'bg-yellow-500' : 'bg-green-500'}`}
                style={{ width: `${memPercent}%` }}
              />
            </div>
            <div className="mt-1 text-xs text-gray-500">
              {system.memory_used_gb?.toFixed(1) || 0} GB / {system.memory_total_gb?.toFixed(1) || 0} GB
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function PropagationMethodsCard() {
  const [expanded, setExpanded] = useState(false)
  
  const { data } = useQuery({
    queryKey: ['performance-stats'],
    queryFn: async () => {
      const res = await fetch('/api/v1/performance/stats')
      return res.json()
    },
    refetchInterval: 5000,
  })
  
  const health = data?.health || {}
  const propagation = data?.propagation || {}
  
  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-yellow-400" />
          <h3 className="font-medium">Propagation Engines</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded ${health.overall === 'healthy' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
            {health.overall}
          </span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && (
        <div className="p-4 pt-0 space-y-2">
          {/* SGP4 */}
          <div className="bg-spacex-card rounded p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-white">SGP4 (In-Process)</span>
              <span className="text-xs px-2 py-0.5 rounded bg-green-500/20 text-green-400">
                {health.sgp4}
              </span>
            </div>
            <div className="text-xs text-gray-400 space-y-1">
              <div>Avg latency: <span className="text-white font-mono">{propagation.sgp4?.avg_latency_ms || 2.8}ms</span></div>
              <div>Satellites: <span className="text-white font-mono">{propagation.sgp4?.satellite_count || 0}</span></div>
            </div>
          </div>
          
          {/* SPICE */}
          <div className="bg-spacex-card rounded p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-white">SPICE (OMM/Batch)</span>
              <span className={`text-xs px-2 py-0.5 rounded ${health.spice === 'online' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>
                {health.spice || 'offline'}
              </span>
            </div>
            <div className="text-xs text-gray-400 space-y-1">
              <div>Batch threshold: <span className="text-white font-mono">{propagation.spice?.batch_threshold || 50} satellites</span></div>
              {health.spice === 'offline' && (
                <div className="text-yellow-400 text-xs mt-1">
                  ⚠️ SPICE unavailable - using SGP4 fallback
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function BenchmarkCard() {
  const [expanded, setExpanded] = useState(false)
  const [running, setRunning] = useState(false)
  const [results, setResults] = useState<any>(null)
  
  const runBenchmark = async () => {
    setRunning(true)
    try {
      const res = await fetch('/api/v1/performance/benchmark?satellite_count=100&runs=3', {
        method: 'POST'
      })
      const data = await res.json()
      setResults(data)
    } catch (error) {
      console.error('Benchmark failed:', error)
    } finally {
      setRunning(false)
    }
  }
  
  return (
    <div className="bg-spacex-dark rounded-lg overflow-hidden">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-spacex-border/30 transition"
      >
        <div className="flex items-center gap-2">
          <BarChart3 size={16} className="text-orange-400" />
          <h3 className="font-medium">Benchmark</h3>
        </div>
        <div className="flex items-center gap-2">
          {results && (
            <span className="text-xs text-gray-400">
              Last: {results.benchmark_duration_sec}s
            </span>
          )}
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>
      
      {expanded && (
        <div className="p-4 pt-0 space-y-3">
          <button
            onClick={runBenchmark}
            disabled={running}
            className={`w-full flex items-center justify-center gap-2 py-2 rounded transition ${
              running 
                ? 'bg-gray-700 text-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            <Play size={16} />
            {running ? 'Running benchmark...' : 'Run Benchmark (100 sats)'}
          </button>
          
          {results && (
            <div className="space-y-2">
              {/* SGP4 Results */}
              <div className="bg-spacex-card rounded p-3">
                <div className="text-sm font-medium text-white mb-2">SGP4 (Parallel)</div>
                <div className="text-xs text-gray-400 space-y-1">
                  <div>Duration: <span className="text-white font-mono">{results.sgp4.avg_duration_ms}ms</span></div>
                  <div>Throughput: <span className="text-white font-mono">{results.sgp4.throughput_per_sec} /s</span></div>
                </div>
              </div>
              
              {/* SPICE Results */}
              {results.spice.available && results.spice.avg_duration_ms && (
                <div className="bg-spacex-card rounded p-3">
                  <div className="text-sm font-medium text-white mb-2">SPICE (Batch)</div>
                  <div className="text-xs text-gray-400 space-y-1">
                    <div>Duration: <span className="text-white font-mono">{results.spice.avg_duration_ms}ms</span></div>
                    <div>Throughput: <span className="text-white font-mono">{results.spice.throughput_per_sec} /s</span></div>
                    <div>Speedup: <span className="text-green-400 font-mono">{results.spice.speedup}x</span></div>
                  </div>
                </div>
              )}
              
              {/* Recommendation */}
              <div className="bg-blue-500/10 border border-blue-500/30 rounded p-3">
                <div className="text-xs text-blue-400">
                  <strong>Recommendation:</strong> {results.recommendation.reason}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
