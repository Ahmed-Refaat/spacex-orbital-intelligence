/**
 * Zod schemas for runtime validation of API responses.
 * 
 * Story 2.4 (P1-6): Runtime Validation with Zod
 * 
 * TypeScript types don't validate at runtime. Zod ensures API responses
 * match expected shape, catching contract violations early.
 * 
 * Usage:
 * ```ts
 * const data = await fetchJson('/api/positions')
 * const validated = PositionsResponseSchema.parse(data)
 * ```
 */

import { z } from 'zod'

// Satellite Position Schema
export const SatellitePositionSchema = z.object({
  id: z.string(),
  lat: z.number().min(-90).max(90),
  lon: z.number().min(-180).max(180),
  alt: z.number().min(0),
  v: z.number().min(0),
})

export type SatellitePosition = z.infer<typeof SatellitePositionSchema>

// Positions Response Schema
export const PositionsResponseSchema = z.object({
  count: z.number(),
  source: z.enum(['tle', 'simulated']),
  positions: z.array(SatellitePositionSchema),
})

// Health Response Schema
export const HealthResponseSchema = z.object({
  status: z.string(),
  satellites_loaded: z.number(),
  cache_connected: z.boolean(),
  last_tle_update: z.string().nullable(),
})

// Launch Schema
export const LaunchSchema = z.object({
  id: z.string(),
  name: z.string(),
  date_utc: z.string(),
  success: z.boolean().nullable(),
  rocket_id: z.string(),
  launchpad_id: z.string(),
  details: z.string().nullable(),
  cores: z.array(z.any()), // Can be refined further
  payload_count: z.number(),
  webcast: z.string().nullable(),
  patch: z.string().nullable(),
})

export const LaunchesResponseSchema = z.object({
  type: z.string(),
  count: z.number(),
  launches: z.array(LaunchSchema),
})

// Satellite Detail Schema
export const SatelliteDetailSchema = z.object({
  satellite_id: z.string(),
  latitude: z.number(),
  longitude: z.number(),
  altitude: z.number(),
  velocity: z.number(),
  timestamp: z.string(),
  name: z.string().optional(),
  tle: z.object({
    line1: z.string().nullable(),
    line2: z.string().nullable(),
  }).optional(),
})

// Orbit Data Schema
export const OrbitPointSchema = z.object({
  t: z.string(),
  lat: z.number(),
  lon: z.number(),
  alt: z.number(),
})

export const OrbitDataSchema = z.object({
  satellite_id: z.string(),
  name: z.string().optional(),
  hours: z.number(),
  step_minutes: z.number(),
  points: z.number(),
  source: z.enum(['tle', 'simulated']),
  orbit: z.array(OrbitPointSchema),
})

// Initial Data Batch Schema (for Story 2.1)
export const InitialDataSchema = z.object({
  positions: PositionsResponseSchema,
  health: HealthResponseSchema,
  launches: LaunchesResponseSchema,
})

// Error Response Schema
export const ErrorResponseSchema = z.object({
  detail: z.string(),
  errors: z.array(z.any()).optional(),
})
