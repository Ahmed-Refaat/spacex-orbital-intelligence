import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import type { SatellitePosition } from '@/types'

const TRAIL_LENGTH = 50 // Number of position history points
const TRAIL_UPDATE_INTERVAL = 100 // ms between trail updates

interface TrailSystem {
  positions: THREE.Vector3[]
  lastUpdate: number
  line: THREE.Line | null
}

interface SatelliteTrailsProps {
  positions: SatellitePosition[]
  enabled: boolean
}

export function SatelliteTrails({ positions, enabled }: SatelliteTrailsProps) {
  const trailsRef = useRef<Map<string, TrailSystem>>(new Map())
  const groupRef = useRef<THREE.Group>(null)

  // Convert lat/lon/alt to 3D position
  const toPosition = (sat: SatellitePosition): THREE.Vector3 => {
    const EARTH_RADIUS = 6.371
    const ALTITUDE_SCALE = 0.015
    
    const phi = (90 - sat.lat) * (Math.PI / 180)
    const theta = (sat.lon + 180) * (Math.PI / 180)
    const altitudeOffset = (sat.alt / 100) * ALTITUDE_SCALE
    const r = EARTH_RADIUS + altitudeOffset

    return new THREE.Vector3(
      -r * Math.sin(phi) * Math.cos(theta),
      r * Math.cos(phi),
      r * Math.sin(phi) * Math.sin(theta)
    )
  }

  useFrame(() => {
    if (!enabled || !groupRef.current) return

    const now = Date.now()

    positions.forEach(sat => {
      let trail = trailsRef.current.get(sat.id)
      
      if (!trail) {
        trail = {
          positions: [],
          lastUpdate: 0,
          line: null
        }
        trailsRef.current.set(sat.id, trail)
      }

      // Update trail at intervals
      if (now - trail.lastUpdate > TRAIL_UPDATE_INTERVAL) {
        const position = toPosition(sat)
        trail.positions.push(position)
        
        // Keep only last N positions
        if (trail.positions.length > TRAIL_LENGTH) {
          trail.positions.shift()
        }
        
        trail.lastUpdate = now

        // Update or create line geometry
        if (trail.positions.length >= 2) {
          // Remove old line
          if (trail.line) {
            groupRef.current?.remove(trail.line)
            trail.line.geometry.dispose()
            ;(trail.line.material as THREE.Material).dispose()
          }

          // Create gradient colors (fade from bright to transparent)
          const colors: number[] = []
          const positions = trail.positions
          
          positions.forEach((_, index) => {
            const alpha = index / positions.length
            const color = new THREE.Color()
            
            // Color based on altitude
            if (sat.alt < 400) {
              color.setHSL(0.33, 1, 0.5) // Green
            } else if (sat.alt < 600) {
              color.setHSL(0.6, 1, 0.5) // Blue
            } else if (sat.alt < 800) {
              color.setHSL(0.12, 1, 0.5) // Yellow
            } else {
              color.setHSL(0, 1, 0.5) // Red
            }
            
            // Apply fade
            colors.push(color.r * alpha, color.g * alpha, color.b * alpha)
          })

          const geometry = new THREE.BufferGeometry().setFromPoints(positions)
          geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))

          const material = new THREE.LineBasicMaterial({
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending,
            linewidth: 2
          })

          trail.line = new THREE.Line(geometry, material)
          groupRef.current?.add(trail.line)
        }
      }
    })

    // Cleanup old trails (satellites no longer in view)
    const currentIds = new Set(positions.map(s => s.id))
    for (const [id, trail] of trailsRef.current.entries()) {
      if (!currentIds.has(id)) {
        if (trail.line) {
          groupRef.current?.remove(trail.line)
          trail.line.geometry.dispose()
          ;(trail.line.material as THREE.Material).dispose()
        }
        trailsRef.current.delete(id)
      }
    }
  })

  if (!enabled) return null

  return <group ref={groupRef} />
}
