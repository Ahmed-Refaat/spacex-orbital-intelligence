import { useState } from 'react'
import { Play, Pause, Sparkles, Zap, Camera, Globe } from 'lucide-react'

interface VisualEffectsControls {
  trails: boolean
  collisions: boolean
  atmosphere: boolean
  aurora: boolean
  cityLights: boolean
  cinematicMode: 'none' | 'overview' | 'constellation' | 'conjunction' | 'launch' | 'imax'
}

interface VisualEffectsPanelProps {
  controls: VisualEffectsControls
  onChange: (controls: VisualEffectsControls) => void
  onPlayCinematic: (sequence: string) => void
}

export function VisualEffectsPanel({ controls, onChange, onPlayCinematic }: VisualEffectsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  const toggleEffect = (key: keyof VisualEffectsControls) => {
    if (typeof controls[key] === 'boolean') {
      onChange({ ...controls, [key]: !controls[key] })
    }
  }

  return (
    <div className="fixed bottom-4 left-4 w-80 z-40">
      <div className="bg-gradient-to-br from-gray-900/98 via-purple-900/20 to-gray-900/98 backdrop-blur-md rounded-2xl shadow-2xl border border-purple-500/20">
        {/* Header */}
        <div 
          className="flex items-center justify-between p-4 border-b border-purple-500/20 cursor-pointer hover:bg-purple-500/5 transition-all rounded-t-2xl"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-purple-500/20 rounded-lg">
              <Sparkles className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h3 className="font-semibold text-white text-sm">Visual Effects</h3>
              <p className="text-[10px] text-gray-400">Cinematic controls</p>
            </div>
          </div>
          <span className="text-purple-400 text-sm font-bold">
            {isExpanded ? '▼' : '▶'}
          </span>
        </div>

      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Effects Toggles */}
          <div className="space-y-2.5">
            <p className="text-[10px] text-purple-300 uppercase font-bold tracking-wider mb-3">Visual Effects</p>
            
            <EffectToggle
              icon={<Sparkles className="w-4 h-4" />}
              label="Satellite Trails"
              description="Flowing light trails"
              enabled={controls.trails}
              onToggle={() => toggleEffect('trails')}
              color="text-blue-400"
            />
            
            <EffectToggle
              icon={<Zap className="w-4 h-4" />}
              label="Collision Alerts"
              description="Near-miss visualization"
              enabled={controls.collisions}
              onToggle={() => toggleEffect('collisions')}
              color="text-red-400"
            />
            
            <EffectToggle
              icon={<Globe className="w-4 h-4" />}
              label="Atmosphere"
              description="Glowing atmosphere"
              enabled={controls.atmosphere}
              onToggle={() => toggleEffect('atmosphere')}
              color="text-cyan-400"
            />
            
            <EffectToggle
              icon={<Sparkles className="w-4 h-4" />}
              label="Aurora"
              description="Polar lights"
              enabled={controls.aurora}
              onToggle={() => toggleEffect('aurora')}
              color="text-green-400"
            />
            
            <EffectToggle
              icon={<Globe className="w-4 h-4" />}
              label="City Lights"
              description="Night side cities"
              enabled={controls.cityLights}
              onToggle={() => toggleEffect('cityLights')}
              color="text-yellow-400"
            />
          </div>

          {/* Cinematic Sequences */}
          <div className="space-y-2 pt-4 border-t border-purple-500/20">
            <p className="text-[10px] text-purple-300 uppercase font-bold tracking-wider mb-3 flex items-center gap-1.5">
              <Camera className="w-3.5 h-3.5" />
              Cinematic Sequences
            </p>
            
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => onPlayCinematic('overview')}
                className="px-3 py-2.5 bg-gradient-to-br from-purple-600/90 to-purple-700/90 hover:from-purple-600 hover:to-purple-700 text-white rounded-lg text-xs font-semibold transition-all shadow-lg hover:shadow-purple-500/50 flex items-center justify-center gap-1.5 hover:scale-105 active:scale-95"
              >
                <Play className="w-3.5 h-3.5" />
                Overview
              </button>
              
              <button
                onClick={() => onPlayCinematic('constellation')}
                className="px-3 py-2.5 bg-gradient-to-br from-blue-600/90 to-blue-700/90 hover:from-blue-600 hover:to-blue-700 text-white rounded-lg text-xs font-semibold transition-all shadow-lg hover:shadow-blue-500/50 flex items-center justify-center gap-1.5 hover:scale-105 active:scale-95"
              >
                <Play className="w-3.5 h-3.5" />
                Constellation
              </button>
              
              <button
                onClick={() => onPlayCinematic('conjunction')}
                className="px-3 py-2.5 bg-gradient-to-br from-red-600/90 to-red-700/90 hover:from-red-600 hover:to-red-700 text-white rounded-lg text-xs font-semibold transition-all shadow-lg hover:shadow-red-500/50 flex items-center justify-center gap-1.5 hover:scale-105 active:scale-95"
              >
                <Play className="w-3.5 h-3.5" />
                Close Approach
              </button>
              
              <button
                onClick={() => onPlayCinematic('launch')}
                className="px-3 py-2.5 bg-gradient-to-br from-orange-600/90 to-orange-700/90 hover:from-orange-600 hover:to-orange-700 text-white rounded-lg text-xs font-semibold transition-all shadow-lg hover:shadow-orange-500/50 flex items-center justify-center gap-1.5 hover:scale-105 active:scale-95"
              >
                <Play className="w-3.5 h-3.5" />
                Launch
              </button>
            </div>
            
            {/* IMAX Mode - Special */}
            <button
              onClick={() => onPlayCinematic('imax')}
              className="w-full px-4 py-3.5 bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 hover:from-purple-500 hover:via-pink-500 hover:to-red-500 text-white rounded-xl text-sm font-bold transition-all shadow-xl hover:shadow-2xl hover:shadow-pink-500/50 transform hover:scale-105 active:scale-95 flex items-center justify-center gap-2.5 mt-3"
            >
              <Sparkles className="w-5 h-5 animate-pulse" />
              🎬 IMAX MODE
              <Sparkles className="w-5 h-5 animate-pulse" />
            </button>
          </div>

          {/* Performance Warning */}
          {(controls.trails || controls.aurora || controls.cityLights) && (
            <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-xs text-yellow-300 flex items-start gap-2">
              <span className="text-base">⚠️</span>
              <span className="leading-relaxed">High-performance effects active. May impact framerate on slower devices.</span>
            </div>
          )}
        </div>
      )}
      </div>
    </div>
  )
}

interface EffectToggleProps {
  icon: React.ReactNode
  label: string
  description: string
  enabled: boolean
  onToggle: () => void
  color: string
}

function EffectToggle({ icon, label, description, enabled, onToggle, color }: EffectToggleProps) {
  return (
    <button
      onClick={onToggle}
      className={`w-full p-3 rounded-lg border transition-all text-left group hover:scale-[1.02] active:scale-[0.98] ${
        enabled
          ? 'bg-gradient-to-br from-purple-900/40 to-purple-800/20 border-purple-500/40 shadow-lg shadow-purple-500/10'
          : 'bg-gray-800/20 border-gray-700/30 hover:bg-gray-800/40 hover:border-gray-600/40'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 flex-1">
          <div className={`mt-0.5 transition-colors ${enabled ? color : 'text-gray-500'}`}>
            {icon}
          </div>
          <div className="flex-1">
            <div className={`text-sm font-semibold transition-colors ${enabled ? 'text-white' : 'text-gray-400 group-hover:text-gray-300'}`}>
              {label}
            </div>
            <div className="text-[10px] text-gray-500 mt-0.5 leading-tight">
              {description}
            </div>
          </div>
        </div>
        <div className={`w-11 h-6 rounded-full relative transition-all flex-shrink-0 ${
          enabled ? 'bg-gradient-to-r from-green-500 to-emerald-500 shadow-lg shadow-green-500/30' : 'bg-gray-700'
        }`}>
          <div className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow-md transition-transform ${
            enabled ? 'translate-x-6' : 'translate-x-1'
          }`} />
        </div>
      </div>
    </button>
  )
}
