/**
 * Custom hook for managing OrbitControls.
 * 
 * Story 2.2 (P0-2): Replace Global Mutation with useRef
 * 
 * Replaces window.__orbitControls mutation with React ref pattern.
 * Type-safe, testable, and React-idiomatic.
 * 
 * Usage:
 * ```tsx
 * const { controlsRef, zoom } = useOrbitControls()
 * 
 * <OrbitControls ref={controlsRef} ... />
 * 
 * <button onClick={() => zoom(-3)}>Zoom In</button>
 * <button onClick={() => zoom(3)}>Zoom Out</button>
 * ```
 */

import { useRef, useCallback } from 'react'

export function useOrbitControls() {
  const controlsRef = useRef<any>(null)
  
  const zoom = useCallback((delta: number) => {
    if (!controlsRef.current) return
    
    const camera = controlsRef.current.object
    const currentDistance = camera.position.length()
    
    // Clamp between min and max distance
    const newDistance = Math.max(8, Math.min(50, currentDistance + delta))
    
    camera.position.setLength(newDistance)
    controlsRef.current.update()
  }, [])
  
  return {
    controlsRef,
    zoom,
  }
}
