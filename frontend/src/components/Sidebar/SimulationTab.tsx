import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useStore } from '@/stores/useStore'
import { simulateDeorbit } from '@/services/api'
import { PlayCircle, RotateCcw, AlertTriangle, Sun, Radio, Info } from 'lucide-react'

// Types for simulation results
interface DeorbitResult {
  initial_altitude_km: number
  estimated_reentry_hours: number
  trajectory_sample: Array<{ altitude_km: number; time_hours: number }>
}

export function SimulationTab() {
  const { selectedSatelliteId } = useStore()

  return (
    <div className="space-y-6">
      {/* Info */}
      <div className="bg-spacex-dark rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <PlayCircle size={16} className="text-spacex-accent" />
          <h3 className="font-medium">Simulation Suite</h3>
        </div>
        <p className="text-sm text-gray-400">
          Monte-Carlo launch simulations, deorbit trajectories, and collision scenarios.
        </p>
      </div>

      {/* Launch Simulator (NEW!) */}
      <LaunchSimulator />

      {/* Deorbit Simulation */}
      <DeorbitSimulation satelliteId={selectedSatelliteId} />

      {/* Eclipse Prediction */}
      <EclipsePrediction satelliteId={selectedSatelliteId} />
      
      {/* Link Budget */}
      <LinkBudgetCard satelliteId={selectedSatelliteId} />
    </div>
  )
}

function EclipsePrediction({ satelliteId }: { satelliteId: string | null }) {
  const { data, isLoading } = useQuery({
    queryKey: ['eclipse', satelliteId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/analysis/eclipse/${satelliteId}?hours_ahead=24`)
      return res.json()
    },
    enabled: !!satelliteId,
    staleTime: 60000,
  })

  if (!satelliteId) {
    return (
      <div className="bg-spacex-dark rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sun size={16} className="text-yellow-400" />
          <h3 className="font-medium">Eclipse Prediction</h3>
        </div>
        <p className="text-sm text-gray-400">
          Select a satellite to predict eclipse periods.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sun size={16} className="text-yellow-400" />
        <h3 className="font-medium">Eclipse Prediction</h3>
      </div>
      
      {isLoading ? (
        <div className="animate-pulse h-16 bg-spacex-border rounded" />
      ) : data?.eclipses?.length > 0 ? (
        <div className="space-y-2">
          <div className="text-xs text-gray-400">
            {data.eclipse_count} eclipse(s) in next 24h
          </div>
          {data.eclipses.slice(0, 3).map((eclipse: any, i: number) => (
            <div key={i} className="bg-spacex-card rounded p-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-400">Start:</span>
                <span>{new Date(eclipse.start).toLocaleTimeString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Duration:</span>
                <span>{eclipse.duration_minutes} min</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-sm text-green-400">
          ☀️ No eclipses predicted in next 24h
        </div>
      )}
    </div>
  )
}

function LinkBudgetCard({ satelliteId }: { satelliteId: string | null }) {
  const [station, setStation] = useState('Cape Canaveral')
  
  const { data, isLoading } = useQuery({
    queryKey: ['link-budget', satelliteId, station],
    queryFn: async () => {
      const res = await fetch(`/api/v1/analysis/link-budget/${satelliteId}?ground_station=${encodeURIComponent(station)}`)
      return res.json()
    },
    enabled: !!satelliteId,
    staleTime: 30000,
  })

  if (!satelliteId) {
    return (
      <div className="bg-spacex-dark rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Radio size={16} className="text-cyan-400" />
          <h3 className="font-medium">Link Budget</h3>
        </div>
        <p className="text-sm text-gray-400">
          Select a satellite to calculate link budget.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Radio size={16} className="text-cyan-400" />
        <h3 className="font-medium">Link Budget</h3>
      </div>
      
      <select
        value={station}
        onChange={(e) => setStation(e.target.value)}
        className="w-full mb-3 bg-spacex-card border border-spacex-border rounded px-2 py-1.5 text-sm"
      >
        <option>Cape Canaveral</option>
        <option>Vandenberg</option>
        <option>Alaska (Fairbanks)</option>
        <option>Hawaii (AMOS)</option>
        <option>Svalbard (SvalSat)</option>
      </select>
      
      {isLoading ? (
        <div className="animate-pulse h-20 bg-spacex-border rounded" />
      ) : data?.link_performance ? (
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-400">Elevation</span>
            <span>{data.geometry.elevation_deg.toFixed(1)}°</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Slant Range</span>
            <span>{data.geometry.slant_range_km.toFixed(0)} km</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Path Loss</span>
            <span>{data.losses.total_loss_db.toFixed(1)} dB</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-400">Link Status</span>
            <span className={`px-2 py-0.5 rounded text-xs ${
              data.link_performance.link_status === 'GOOD' ? 'bg-green-500/20 text-green-400' :
              data.link_performance.link_status === 'MARGINAL' ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-red-500/20 text-red-400'
            }`}>
              {data.link_performance.link_status}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Link Margin</span>
            <span className={data.link_performance.link_margin_db > 0 ? 'text-green-400' : 'text-red-400'}>
              {data.link_performance.link_margin_db.toFixed(1)} dB
            </span>
          </div>
        </div>
      ) : data?.detail ? (
        <div className="text-sm text-red-400">{data.detail}</div>
      ) : (
        <div className="text-sm text-gray-400">No data available</div>
      )}
    </div>
  )
}

function DeorbitSimulation({ satelliteId }: { satelliteId: string | null }) {
  const [deltaV, setDeltaV] = useState(0.1)
  
  const mutation = useMutation<DeorbitResult>({
    mutationFn: () => simulateDeorbit(satelliteId!, deltaV) as Promise<DeorbitResult>,
  })

  if (!satelliteId) {
    return (
      <div className="bg-spacex-dark rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <RotateCcw size={16} className="text-yellow-400" />
          <h3 className="font-medium">Deorbit Simulation</h3>
        </div>
        <p className="text-sm text-gray-400">
          Select a satellite to simulate its deorbit trajectory.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <RotateCcw size={16} className="text-yellow-400" />
        <h3 className="font-medium">Deorbit Simulation</h3>
      </div>

      <div className="space-y-4">
        <div className="text-sm">
          <span className="text-gray-400">Target: </span>
          <span className="font-mono">{satelliteId}</span>
        </div>

        {/* Delta-V slider */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">Deorbit ΔV</span>
            <span>{deltaV.toFixed(2)} km/s</span>
          </div>
          <input
            type="range"
            min={0.01}
            max={1.0}
            step={0.01}
            value={deltaV}
            onChange={(e) => setDeltaV(parseFloat(e.target.value))}
            className="w-full accent-spacex-accent"
          />
        </div>

        {/* Run button */}
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="w-full py-2 bg-spacex-accent hover:bg-blue-600 disabled:opacity-50 rounded-lg text-sm font-medium transition"
        >
          {mutation.isPending ? 'Simulating...' : 'Run Simulation'}
        </button>

        {/* Results */}
        {mutation.data && (
          <div className="mt-4 p-3 bg-spacex-card rounded-lg border border-spacex-border">
            <h4 className="font-medium text-sm mb-2">Simulation Results</h4>
            
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs text-gray-400">Initial Altitude</div>
                <div>{mutation.data.initial_altitude_km?.toFixed(1)} km</div>
              </div>
              <div>
                <div className="text-xs text-gray-400">Reentry Time</div>
                <div>{mutation.data.estimated_reentry_hours} hours</div>
              </div>
            </div>

            {/* Trajectory preview */}
            <div className="mt-3">
              <div className="text-xs text-gray-400 mb-1">Altitude Decay</div>
              <div className="h-24 bg-spacex-dark rounded flex items-end p-2 gap-0.5">
                {mutation.data.trajectory_sample?.slice(0, 30).map((point: { altitude_km: number }, i: number) => (
                  <div
                    key={i}
                    className="flex-1 bg-gradient-to-t from-red-500 to-blue-500 rounded-t"
                    style={{ 
                      height: `${Math.max(5, (point.altitude_km / mutation.data.initial_altitude_km) * 100)}%` 
                    }}
                  />
                ))}
              </div>
            </div>

            <div className="mt-2 flex items-center gap-1 text-xs text-yellow-400">
              <AlertTriangle size={12} />
              Simplified model - actual results may vary
            </div>
          </div>
        )}

        {mutation.error && (
          <div className="text-sm text-red-400">
            Simulation failed. Please try again.
          </div>
        )}
      </div>
    </div>
  )
}

function LaunchSimulator() {
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [params, setParams] = useState({
    thrust_variance: 0.05,
    n_runs: 1000
  })

  const runSimulation = async () => {
    setRunning(true)
    setResult(null)
    
    try {
      const res = await fetch('/api/v1/simulation/launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thrust_N: 8000000,  // Updated to match backend defaults
          thrust_variance: params.thrust_variance,
          Isp: 360,  // Updated to match backend defaults
          n_runs: params.n_runs
        })
      })
      
      const data = await res.json()
      
      if (data.status === 'complete') {
        setResult(data)
        setRunning(false)
      } else if (data.status === 'running') {
        // Poll for results
        const simId = data.sim_id
        const pollResult = async () => {
          const pollRes = await fetch(`/api/v1/simulation/launch/${simId}`)
          const pollData = await pollRes.json()
          
          if (pollData.status === 'complete') {
            setResult(pollData)
            setRunning(false)
          } else if (pollData.status === 'running') {
            setTimeout(pollResult, 2000)
          } else {
            setRunning(false)
          }
        }
        setTimeout(pollResult, 2000)
      }
    } catch (error) {
      console.error('Simulation failed:', error)
      setRunning(false)
    }
  }

  return (
    <div className="bg-spacex-dark rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <PlayCircle size={16} className="text-orange-400" />
        <h3 className="font-medium">Launch Simulator</h3>
      </div>
      
      {/* Explanation */}
      <div className="mb-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
        <div className="flex items-start gap-2 mb-2">
          <Info size={14} className="text-blue-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-blue-200">
            <strong className="text-blue-300">Simulation Monte-Carlo</strong>
          </div>
        </div>
        <div className="text-xs text-gray-300 space-y-1.5 ml-5">
          <p>
            <strong className="text-white">Fusée:</strong> Single-Stage-To-Orbit (SSTO) théorique<br />
            <span className="text-gray-400">• Thrust: 8 MN • Isp: 360s • Masse: 615t</span>
          </p>
          <p>
            <strong className="text-white">Mission:</strong> Atteindre 180km d'altitude + 7.5 km/s de vitesse orbitale
          </p>
          <p>
            <strong className="text-white">Monte-Carlo:</strong> Teste {params.n_runs.toLocaleString()}x avec incertitudes aléatoires (±{(params.thrust_variance * 100).toFixed(0)}% thrust, ±3% Isp, ±2% masse)
          </p>
          <p className="text-yellow-300/80">
            ⚠️ SSTO est physiquement très difficile - success rate faible est réaliste
          </p>
        </div>
      </div>

      {/* Parameters */}
      <div className="space-y-3 mb-4">
        <div>
          <label className="text-xs text-gray-400 mb-1 block">
            Incertitude Thrust (±{(params.thrust_variance * 100).toFixed(0)}%)
          </label>
          <input
            type="range"
            min="0"
            max="0.20"
            step="0.01"
            value={params.thrust_variance}
            onChange={(e) => setParams({ ...params, thrust_variance: parseFloat(e.target.value) })}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            disabled={running}
          />
        </div>

        <div>
          <label className="text-xs text-gray-400 mb-1 block">
            Nombre de tests: {params.n_runs.toLocaleString()}
          </label>
          <input
            type="range"
            min="100"
            max="5000"
            step="100"
            value={params.n_runs}
            onChange={(e) => setParams({ ...params, n_runs: parseInt(e.target.value) })}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            disabled={running}
          />
        </div>
      </div>

      {/* Run Button */}
      <button
        onClick={runSimulation}
        disabled={running}
        className={`w-full py-2 rounded flex items-center justify-center gap-2 transition ${
          running
            ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
            : 'bg-orange-600 hover:bg-orange-700 text-white'
        }`}
      >
        <PlayCircle size={16} />
        {running ? 'Simulation en cours...' : 'Lancer Simulation'}
      </button>

      {/* Results */}
      {result && result.status === 'complete' && (
        <div className="mt-4 space-y-3">
          <div className="bg-spacex-card rounded p-3">
            <div className="text-xs text-gray-400 mb-1">Taux de Succès</div>
            <div className={`text-2xl font-bold ${
              (result.success_rate || 0) > 0.9 ? 'text-green-400' :
              (result.success_rate || 0) > 0.7 ? 'text-yellow-400' : 
              (result.success_rate || 0) > 0 ? 'text-orange-400' : 'text-red-400'
            }`}>
              {typeof result.success_rate === 'number' ? (result.success_rate * 100).toFixed(1) : '0.0'}%
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {result.success_count || 0} / {result.total_runs || 0} lancements réussis
            </div>
          </div>

          {/* Failure Modes */}
          {result.failure_modes && Object.keys(result.failure_modes).length > 0 && (
            <div className="bg-spacex-card rounded p-3">
              <div className="text-xs text-gray-400 mb-2">Modes d'Échec</div>
              {Object.entries(result.failure_modes).map(([mode, count]: [string, any]) => (
                <div key={mode} className="flex justify-between text-xs mb-1">
                  <span className="text-gray-500">
                    {mode === 'fuel_depletion' ? '⛽ Plus de carburant' :
                     mode === 'insufficient_velocity' ? '🚀 Vitesse insuffisante' :
                     mode === 'structural_failure' ? '💥 Rupture structure' :
                     mode === 'crashed' ? '💀 Crash' :
                     mode.replace(/_/g, ' ')}
                  </span>
                  <span className="text-white">{count}</span>
                </div>
              ))}
            </div>
          )}

          <div className="text-xs text-gray-500">
            Runtime: {result.runtime_seconds?.toFixed(2) || '0.00'}s
          </div>
        </div>
      )}
    </div>
  )
}
