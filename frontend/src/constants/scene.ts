/**
 * Three.js Scene Constants for Orbital Visualization
 * 
 * Scale: 1 Three.js unit = 1000km
 * This provides mathematically correct proportions while keeping
 * the scene at a manageable scale for rendering.
 */

export const EARTH_RADIUS_KM = 6371
export const SCALE_FACTOR = 1000  // 1 Three.js unit = 1000km real
export const EARTH_RADIUS = EARTH_RADIUS_KM / SCALE_FACTOR  // 6.371 units

/**
 * Minimum safe altitude for satellites (below this, atmospheric drag dominates)
 */
export const MIN_ALTITUDE_KM = 150

/**
 * Convert real-world altitude to Three.js scene radius
 * 
 * @param altitude_km - Satellite altitude above Earth surface (km)
 * @returns Scene radius from origin (Three.js units)
 * 
 * Examples:
 * - 200km LEO → 6.571 units (+3.1% from surface)
 * - 550km Starlink → 6.921 units (+8.6% from surface)
 * - 1200km LEO high → 7.571 units (+18.8% from surface)
 */
export function altitudeToSceneRadius(altitude_km: number): number {
  // Safety check: enforce minimum altitude
  const safeAltitude = Math.max(altitude_km, MIN_ALTITUDE_KM)
  
  if (safeAltitude !== altitude_km && altitude_km < MIN_ALTITUDE_KM) {
    console.warn(`Satellite altitude ${altitude_km}km below minimum (${MIN_ALTITUDE_KM}km), clamped`)
  }
  
  return (EARTH_RADIUS_KM + safeAltitude) / SCALE_FACTOR
}

/**
 * Convert latitude/longitude/altitude to Three.js 3D position
 * 
 * @param lat - Latitude in degrees (-90 to +90)
 * @param lon - Longitude in degrees (-180 to +180)
 * @param alt - Altitude above Earth surface in km
 * @returns Three.js position vector {x, y, z}
 */
export function latLonAltToPosition(lat: number, lon: number, alt: number) {
  const phi = (90 - lat) * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)
  const r = altitudeToSceneRadius(alt)
  
  return {
    x: -r * Math.sin(phi) * Math.cos(theta),
    y: r * Math.cos(phi),
    z: r * Math.sin(phi) * Math.sin(theta)
  }
}
