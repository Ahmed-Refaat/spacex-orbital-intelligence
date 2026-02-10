import { Suspense, useEffect, useRef } from 'react'
import { Canvas } from '@react-three/fiber'
import { Stars, PerspectiveCamera } from '@react-three/drei'
import { Earth } from './Earth'
import { Satellites, SelectedSatelliteHighlight } from './Satellites'
import { OrbitPath } from './OrbitPath'
import { SatelliteTrails } from './SatelliteTrails'
import { CollisionVisualization, generateMockConjunctions } from './CollisionVisualization'
import { CinematicCamera, type CinematicCameraControls } from './CinematicCamera'
import { AtmosphereGlow, AuroraEffect, CityLights } from './AtmosphereGlow'
// import { VisualEffectsPanel } from '../VisualEffectsPanel' // Disabled for now
import { useStore } from '@/stores/useStore'
import { useOrbitControls } from '@/hooks/useOrbitControls'
import { Maximize2, Minimize2 } from 'lucide-react'

// interface VisualEffects {
//   trails: boolean
//   collisions: boolean
//   atmosphere: boolean
//   aurora: boolean
//   cityLights: boolean
//   cinematicMode: 'none' | 'overview' | 'constellation' | 'conjunction' | 'launch' | 'imax'
// }

export function Globe() {
  const { satellites } = useStore()
  const { zoom } = useOrbitControls()
  const cinematicControlsRef = useRef<CinematicCameraControls | null>(null)
  
  // Visual effects state - Hardcoded for now while panel is disabled
  const visualEffects = {
    trails: false,
    collisions: false,
    atmosphere: false,
    aurora: false,
    cityLights: false,
    cinematicMode: 'none' as const
  }

  // Generate mock conjunctions for demo
  const conjunctions = visualEffects.collisions && satellites.length > 0
    ? generateMockConjunctions(satellites)
    : []

  // Handle cinematic sequence playback - Disabled for now
  /*
  const handlePlayCinematic = async (sequence: string) => {
    if (!cinematicControlsRef.current) return
    
    if (sequence === 'imax') {
      // Play full IMAX sequence
      await playImaxSequence(cinematicControlsRef.current, setVisualEffects)
    } else {
      await cinematicControlsRef.current.playSequence(
        sequence as 'overview' | 'constellation' | 'conjunction' | 'launch'
      )
    }
  }
  */

  return (
    <div className="canvas-container w-full h-full">
      <Canvas>
        <PerspectiveCamera makeDefault position={[0, 0, 20]} fov={45} />
        
        {/* Lighting */}
        <ambientLight intensity={0.3} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <directionalLight position={[-10, -10, -5]} intensity={0.3} />
        
        {/* Stars background */}
        <Stars 
          radius={100} 
          depth={50} 
          count={5000} 
          factor={4} 
          saturation={0} 
          fade 
          speed={1}
        />

        <Suspense fallback={null}>
          {/* Earth */}
          <Earth />
          
          {/* Atmosphere effects */}
          <AtmosphereGlow enabled={visualEffects.atmosphere} />
          <AuroraEffect enabled={visualEffects.aurora} />
          <CityLights enabled={visualEffects.cityLights} />
          
          {/* Satellites */}
          <Satellites positions={satellites} />
          
          {/* Satellite trails */}
          <SatelliteTrails positions={satellites} enabled={visualEffects.trails} />
          
          {/* Selected satellite highlight */}
          <SelectedSatelliteHighlight />
          
          {/* Orbital path visualization */}
          <OrbitPath />
          
          {/* Collision visualization */}
          <CollisionVisualization 
            conjunctions={conjunctions} 
            enabled={visualEffects.collisions} 
          />
        </Suspense>

        {/* Cinematic Camera Controls */}
        <CinematicCamera 
          onControlsReady={(controls) => {
            cinematicControlsRef.current = controls
          }}
        />
      </Canvas>

      {/* Visual Effects Control Panel - Disabled for now */}
      {/* <VisualEffectsPanel
        controls={visualEffects}
        onChange={setVisualEffects}
        onPlayCinematic={handlePlayCinematic}
      /> */}

      {/* Overlay UI */}
      <GlobeOverlay zoom={zoom} />
    </div>
  )
}

// IMAX Mode - Ultimate cinematic sequence - Disabled for now
/*
async function playImaxSequence(
  controls: CinematicCameraControls,
  setEffects: React.Dispatch<React.SetStateAction<VisualEffects>>
) {
  // Enable all effects
  setEffects({
    trails: true,
    collisions: true,
    atmosphere: true,
    aurora: true,
    cityLights: true,
    cinematicMode: 'imax'
  })
  
  // Play sequence
  await controls.playSequence('overview')
  await new Promise(resolve => setTimeout(resolve, 1000))
  await controls.playSequence('constellation')
  await new Promise(resolve => setTimeout(resolve, 1000))
  await controls.playSequence('conjunction')
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  // Return to normal
  setEffects(prev => ({ ...prev, cinematicMode: 'none' }))
}
*/

function GlobeOverlay({ zoom }: { zoom: (delta: number) => void }) {
  const { lastUpdate, stats, isFullscreen, toggleFullscreen } = useStore()
  
  // Listen for fullscreen changes (ESC key, etc.)
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isNowFullscreen = !!document.fullscreenElement
      if (isNowFullscreen !== useStore.getState().isFullscreen) {
        useStore.setState({ 
          isFullscreen: isNowFullscreen,
          sidebarOpen: !isNowFullscreen
        })
      }
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  // Format number in scientific notation
  const formatScientific = (num: number) => {
    if (num === 0) return '0'
    const exp = Math.floor(Math.log10(Math.abs(num)))
    const mantissa = (num / Math.pow(10, exp)).toFixed(2)
    const superscript = exp.toString().split('').map(c => 
      c === '-' ? '⁻' : '⁰¹²³⁴⁵⁶⁷⁸⁹'[parseInt(c)]
    ).join('')
    return `${mantissa} × 10${superscript}`
  }

  return (
    <>
      {/* Zoom controls */}
      <div className="absolute top-4 right-4 flex flex-col gap-1">
        <button
          onClick={() => zoom(-3)}
          className="w-10 h-10 glass rounded-lg flex items-center justify-center text-xl font-bold hover:bg-white/10 transition"
        >
          +
        </button>
        <button
          onClick={() => zoom(3)}
          className="w-10 h-10 glass rounded-lg flex items-center justify-center text-xl font-bold hover:bg-white/10 transition"
        >
          −
        </button>
        <button
          onClick={toggleFullscreen}
          className="w-10 h-10 glass rounded-lg flex items-center justify-center hover:bg-white/10 transition mt-2"
          title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        >
          {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
        </button>
      </div>

      {/* Stats overlay - Left side */}
      <div className="absolute bottom-4 left-4">
        <div className="glass rounded-xl p-4">
          {/* Time */}
          {lastUpdate && (
            <div className="text-[10px] text-gray-600 mb-2 font-mono text-left">
              {lastUpdate.toLocaleTimeString()}
            </div>
          )}
          
          {/* Altitude Legend */}
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Altitude Legend</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-gray-400">&lt;400km</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              <span className="text-gray-400">400-600</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-yellow-500" />
              <span className="text-gray-400">600-800</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-gray-400">&gt;800km</span>
            </div>
          </div>
          
          {/* Stats */}
          <div className="flex items-start gap-6 mt-3 pt-3 border-t border-white/10">
            <div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wider">Satellites</div>
              <div className="text-xl font-bold text-blue-400 font-mono">
                {stats.totalSatellites.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wider">Avg Alt</div>
              <div className="text-sm font-bold text-green-400 font-mono">
                ≈ {formatScientific(stats.averageAltitude)} km
              </div>
              <div className="text-sm font-bold text-gray-400 font-mono">
                {formatScientific(stats.averageAltitude / 420 * 100)} %
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
