import { useRef, useCallback, useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { OrbitControls } from '@react-three/drei'

type EasingFunction = (t: number) => number

const easingFunctions: Record<string, EasingFunction> = {
  linear: (t) => t,
  easeInQuad: (t) => t * t,
  easeOutQuad: (t) => t * (2 - t),
  easeInOutQuad: (t) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t),
  easeInCubic: (t) => t * t * t,
  easeOutCubic: (t) => (--t) * t * t + 1,
  easeInOutCubic: (t) => (t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1),
}

interface Animation {
  startTime: number
  duration: number
  startPos: THREE.Vector3
  endPos: THREE.Vector3
  startTarget: THREE.Vector3
  endTarget: THREE.Vector3
  easing: EasingFunction
  onComplete?: () => void
}

export interface CinematicCameraControls {
  flyTo: (target: THREE.Vector3, distance: number, duration?: number, easing?: string) => Promise<void>
  orbitAround: (target: THREE.Vector3, duration: number, rotations?: number) => Promise<void>
  playSequence: (sequence: 'overview' | 'constellation' | 'conjunction' | 'launch') => Promise<void>
  stopAnimation: () => void
}

interface CinematicCameraProps {
  onControlsReady?: (controls: CinematicCameraControls) => void
}

export function CinematicCamera({ onControlsReady }: CinematicCameraProps) {
  const { camera } = useThree()
  const animationRef = useRef<Animation | null>(null)
  const orbitControlsRef = useRef<any>(null)

  const stopAnimation = useCallback(() => {
    animationRef.current = null
    if (orbitControlsRef.current) {
      orbitControlsRef.current.enabled = true
    }
  }, [])

  const animate = useCallback((
    startPos: THREE.Vector3,
    endPos: THREE.Vector3,
    startTarget: THREE.Vector3,
    endTarget: THREE.Vector3,
    duration: number,
    easing: string = 'easeInOutCubic'
  ): Promise<void> => {
    return new Promise((resolve) => {
      animationRef.current = {
        startTime: Date.now(),
        duration,
        startPos: startPos.clone(),
        endPos: endPos.clone(),
        startTarget: startTarget.clone(),
        endTarget: endTarget.clone(),
        easing: easingFunctions[easing] || easingFunctions.easeInOutCubic,
        onComplete: () => {
          animationRef.current = null
          resolve()
        }
      }
      
      if (orbitControlsRef.current) {
        orbitControlsRef.current.enabled = false
      }
    })
  }, [])

  const flyTo = useCallback(async (
    target: THREE.Vector3,
    distance: number,
    duration: number = 2000,
    easing: string = 'easeInOutCubic'
  ) => {
    const currentPos = camera.position.clone()
    const currentTarget = orbitControlsRef.current?.target?.clone() || new THREE.Vector3()
    
    // Calculate end position (distance away from target)
    const direction = currentPos.clone().sub(target).normalize()
    const endPos = target.clone().add(direction.multiplyScalar(distance))
    
    await animate(currentPos, endPos, currentTarget, target, duration, easing)
  }, [camera, animate])

  const orbitAround = useCallback(async (
    target: THREE.Vector3,
    duration: number,
    rotations: number = 1
  ) => {
    const radius = camera.position.distanceTo(target)
    const steps = Math.ceil(duration / 50) // 20fps animation
    const angleStep = (Math.PI * 2 * rotations) / steps
    
    for (let i = 0; i < steps; i++) {
      await new Promise<void>((resolve) => {
        const angle = angleStep * i
        const x = target.x + Math.cos(angle) * radius
        const z = target.z + Math.sin(angle) * radius
        const y = camera.position.y
        
        camera.position.set(x, y, z)
        camera.lookAt(target)
        
        if (orbitControlsRef.current) {
          orbitControlsRef.current.target.copy(target)
          orbitControlsRef.current.update()
        }
        
        setTimeout(resolve, 50)
      })
    }
  }, [camera])

  const playSequence = useCallback(async (
    sequence: 'overview' | 'constellation' | 'conjunction' | 'launch'
  ) => {
    const earthCenter = new THREE.Vector3(0, 0, 0)
    
    switch (sequence) {
      case 'overview':
        // Start far away
        await flyTo(earthCenter, 30, 2000, 'easeInOutCubic')
        // Orbit around Earth
        await orbitAround(earthCenter, 5000, 1)
        // Zoom closer
        await flyTo(earthCenter, 15, 2000, 'easeInOutCubic')
        break
        
      case 'constellation':
        // Focus on Starlink constellation (northern hemisphere, ~550km alt)
        const starlinkFocus = new THREE.Vector3(0, 3, 0)
        await flyTo(starlinkFocus, 10, 2000)
        await orbitAround(starlinkFocus, 4000, 0.5)
        break
        
      case 'conjunction':
        // Dramatic zoom to close approach point
        // (Would need actual conjunction data, using placeholder)
        const conjunctionPoint = new THREE.Vector3(2, 2, 2)
        await flyTo(conjunctionPoint, 0.5, 1500, 'easeInQuad')
        await orbitAround(conjunctionPoint, 3000, 0.5)
        await flyTo(earthCenter, 20, 2000, 'easeOutCubic')
        break
        
      case 'launch':
        // Start at ground level
        const groundPos = new THREE.Vector3(0, -6.371, 0)
        await flyTo(groundPos, 0.5, 1000)
        // Follow up to orbit
        const orbitPos = new THREE.Vector3(0, 7, 0)
        await flyTo(orbitPos, 5, 4000, 'easeInCubic')
        break
    }
    
    // Re-enable controls after sequence
    if (orbitControlsRef.current) {
      orbitControlsRef.current.enabled = true
    }
  }, [flyTo, orbitAround])

  // Update animation
  useFrame(() => {
    const anim = animationRef.current
    if (!anim) return

    const elapsed = Date.now() - anim.startTime
    const progress = Math.min(elapsed / anim.duration, 1)
    const easedProgress = anim.easing(progress)

    // Interpolate position
    camera.position.lerpVectors(anim.startPos, anim.endPos, easedProgress)
    
    // Interpolate target
    const currentTarget = new THREE.Vector3().lerpVectors(
      anim.startTarget,
      anim.endTarget,
      easedProgress
    )
    
    camera.lookAt(currentTarget)
    
    if (orbitControlsRef.current) {
      orbitControlsRef.current.target.copy(currentTarget)
      orbitControlsRef.current.update()
    }

    // Complete animation
    if (progress >= 1 && anim.onComplete) {
      anim.onComplete()
    }
  })

  // Expose controls to parent
  useEffect(() => {
    if (onControlsReady) {
      onControlsReady({
        flyTo,
        orbitAround,
        playSequence,
        stopAnimation
      })
    }
  }, [onControlsReady, flyTo, orbitAround, playSequence, stopAnimation])

  return (
    <OrbitControls
      ref={orbitControlsRef}
      enableDamping
      dampingFactor={0.05}
      minDistance={7}
      maxDistance={50}
    />
  )
}
