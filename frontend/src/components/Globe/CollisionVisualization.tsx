import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { Text } from '@react-three/drei'

interface Conjunction {
  sat1Id: string
  sat2Id: string
  sat1Pos: THREE.Vector3
  sat2Pos: THREE.Vector3
  distance: number // km
  time: Date
}

interface CollisionVisualizationProps {
  conjunctions: Conjunction[]
  enabled: boolean
}

export function CollisionVisualization({ conjunctions, enabled }: CollisionVisualizationProps) {
  const groupRef = useRef<THREE.Group>(null)
  const timeRef = useRef(0)

  useFrame((_, delta) => {
    timeRef.current += delta
  })

  if (!enabled || conjunctions.length === 0) return null

  return (
    <group ref={groupRef}>
      {conjunctions.map((conj, index) => (
        <ConjunctionEffect
          key={`${conj.sat1Id}-${conj.sat2Id}-${index}`}
          conjunction={conj}
          time={timeRef.current}
        />
      ))}
    </group>
  )
}

function ConjunctionEffect({ conjunction, time }: { conjunction: Conjunction; time: number }) {
  const { sat1Pos, sat2Pos, distance } = conjunction
  
  // Calculate midpoint and risk level
  const midpoint = new THREE.Vector3().lerpVectors(sat1Pos, sat2Pos, 0.5)
  
  // Risk level coloring
  const riskColor = useMemo(() => {
    if (distance < 1) return new THREE.Color(0xff0000) // Critical - Red
    if (distance < 2) return new THREE.Color(0xff6600) // High - Orange
    if (distance < 5) return new THREE.Color(0xffaa00) // Medium - Yellow
    return new THREE.Color(0xffff00) // Low - Light Yellow
  }, [distance])

  // Pulsing opacity
  const pulseOpacity = Math.sin(time * 3) * 0.3 + 0.6

  // Line geometry
  const lineGeometry = useMemo(() => {
    return new THREE.BufferGeometry().setFromPoints([sat1Pos, sat2Pos])
  }, [sat1Pos, sat2Pos])

  // Warning sphere scale (pulsing)
  const warningScale = Math.sin(time * 2) * 0.2 + 1.0

  return (
    <group>
      {/* Connecting line between satellites */}
      <primitive object={new THREE.Line(lineGeometry, new THREE.LineBasicMaterial({
        color: riskColor,
        transparent: true,
        opacity: pulseOpacity,
        linewidth: 3
      }))} />

      {/* Danger zone sphere */}
      <mesh position={midpoint}>
        <sphereGeometry args={[distance * 0.01, 16, 16]} />
        <meshBasicMaterial
          color={riskColor}
          transparent
          opacity={0.15}
          wireframe
        />
      </mesh>

      {/* Pulsing warning indicator */}
      <mesh position={midpoint} scale={warningScale}>
        <sphereGeometry args={[0.05, 16, 16]} />
        <meshStandardMaterial
          color={riskColor}
          transparent
          opacity={0.8}
          emissive={riskColor}
          emissiveIntensity={0.5}
        />
      </mesh>

      {/* Outer glow ring */}
      <mesh position={midpoint} rotation={[Math.PI / 2, 0, time]}>
        <ringGeometry args={[0.08, 0.12, 32]} />
        <meshBasicMaterial
          color={riskColor}
          transparent
          opacity={pulseOpacity * 0.6}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Distance label */}
      <Text
        position={[midpoint.x, midpoint.y + 0.15, midpoint.z]}
        fontSize={0.06}
        color="white"
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.003}
        outlineColor="black"
      >
        {`⚠️ ${distance.toFixed(2)} km`}
      </Text>

      {/* Risk level label */}
      <Text
        position={[midpoint.x, midpoint.y + 0.08, midpoint.z]}
        fontSize={0.04}
        color={riskColor}
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.002}
        outlineColor="black"
      >
        {distance < 1 ? 'CRITICAL' : distance < 2 ? 'HIGH RISK' : distance < 5 ? 'MEDIUM' : 'LOW'}
      </Text>

      {/* Light at danger point */}
      <pointLight
        position={midpoint}
        color={riskColor}
        intensity={pulseOpacity * 2}
        distance={1}
      />
    </group>
  )
}

// Mock data generator for demo purposes
export function generateMockConjunctions(satellites: any[]): Conjunction[] {
  const conjunctions: Conjunction[] = []
  
  // Find pairs that are close
  for (let i = 0; i < Math.min(satellites.length, 100); i++) {
    for (let j = i + 1; j < Math.min(satellites.length, 100); j++) {
      const sat1 = satellites[i]
      const sat2 = satellites[j]
      
      // Simple distance check (not accurate, just for visual demo)
      const altDiff = Math.abs(sat1.alt - sat2.alt)
      
      if (altDiff < 50) { // Within 50km altitude
        const latDiff = Math.abs(sat1.lat - sat2.lat)
        const lonDiff = Math.abs(sat1.lon - sat2.lon)
        
        if (latDiff < 10 && lonDiff < 10) { // Rough proximity
          const EARTH_RADIUS = 6.371
          const ALTITUDE_SCALE = 0.015
          
          const toPos = (s: any) => {
            const phi = (90 - s.lat) * (Math.PI / 180)
            const theta = (s.lon + 180) * (Math.PI / 180)
            const altitudeOffset = (s.alt / 100) * ALTITUDE_SCALE
            const r = EARTH_RADIUS + altitudeOffset
            
            return new THREE.Vector3(
              -r * Math.sin(phi) * Math.cos(theta),
              r * Math.cos(phi),
              r * Math.sin(phi) * Math.sin(theta)
            )
          }
          
          const pos1 = toPos(sat1)
          const pos2 = toPos(sat2)
          const distance = pos1.distanceTo(pos2) * 100 // Rough conversion to km
          
          if (distance < 10) { // Within 10km
            conjunctions.push({
              sat1Id: sat1.id,
              sat2Id: sat2.id,
              sat1Pos: pos1,
              sat2Pos: pos2,
              distance: distance,
              time: new Date()
            })
          }
        }
      }
    }
  }
  
  return conjunctions.slice(0, 5) // Show top 5 closest approaches
}
