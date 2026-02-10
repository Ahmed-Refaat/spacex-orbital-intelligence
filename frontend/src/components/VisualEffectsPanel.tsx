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
    <div className="fixed top-20 right-4 bg-gray-900/95 backdrop-blur-sm rounded-lg shadow-xl border border-gray-700 w-72 z-50">
      {/* Header */}
      <div 
        className="flex items-center justify-between p-3 border-b border-gray-700 cursor-pointer hover:bg-gray-800/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-400" />
          <h3 className="font-semibold text-white">Visual Effects</h3>
        </div>
        <span className="text-gray-400 text-sm">
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>

      {isExpanded && (
        <div className="p-3 space-y-4">
          {/* Effects Toggles */}
          <div className="space-y-2">
            <p className="text-xs text-gray-400 uppercase font-semibold mb-2">Effects</p>
            
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
          <div className="space-y-2 pt-3 border-t border-gray-700">
            <p className="text-xs text-gray-400 uppercase font-semibold mb-2">
              <Camera className="w-3 h-3 inline mr-1" />
              Cinematic Sequences
            </p>
            
            <button
              onClick={() => onPlayCinematic('overview')}
              className="w-full px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4" />
              Overview
            </button>
            
            <button
              onClick={() => onPlayCinematic('constellation')}
              className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4" />
              Constellation
            </button>
            
            <button
              onClick={() => onPlayCinematic('conjunction')}
              className="w-full px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4" />
              Close Approach
            </button>
            
            <button
              onClick={() => onPlayCinematic('launch')}
              className="w-full px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4" />
              Launch Sequence
            </button>
            
            {/* IMAX Mode - Special */}
            <button
              onClick={() => onPlayCinematic('imax')}
              className="w-full px-4 py-3 bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 hover:from-purple-700 hover:via-pink-700 hover:to-red-700 text-white rounded-lg text-sm font-bold transition-all shadow-lg hover:shadow-xl transform hover:scale-105 flex items-center justify-center gap-2 mt-3"
            >
              <Sparkles className="w-5 h-5" />
              🎬 IMAX MODE
              <Sparkles className="w-5 h-5" />
            </button>
          </div>

          {/* Performance Warning */}
          {(controls.trails || controls.aurora || controls.cityLights) && (
            <div className="mt-3 p-2 bg-yellow-900/20 border border-yellow-700/50 rounded text-xs text-yellow-300">
              ⚠️ High-performance effects active. May impact framerate on slower devices.
            </div>
          )}
        </div>
      )}
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
      className={`w-full p-2 rounded border transition-all text-left ${
        enabled
          ? 'bg-gray-800/80 border-gray-600'
          : 'bg-gray-800/30 border-gray-700/50 hover:bg-gray-800/50'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-2 flex-1">
          <div className={`mt-0.5 ${enabled ? color : 'text-gray-500'}`}>
            {icon}
          </div>
          <div className="flex-1">
            <div className={`text-sm font-medium ${enabled ? 'text-white' : 'text-gray-400'}`}>
              {label}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {description}
            </div>
          </div>
        </div>
        <div className={`w-10 h-5 rounded-full relative transition-colors ${
          enabled ? 'bg-green-600' : 'bg-gray-600'
        }`}>
          <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
            enabled ? 'left-5' : 'left-0.5'
          }`} />
        </div>
      </div>
    </button>
  )
}
