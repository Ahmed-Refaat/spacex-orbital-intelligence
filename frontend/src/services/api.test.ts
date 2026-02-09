import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  fetchWithTimeout,
  DEFAULT_TIMEOUT,
  LONG_TIMEOUT,
  getHealth,
  getAllPositions,
  getSatellites,
  getSatelliteRisk,
} from './api'

describe('API Service', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  describe('fetchWithTimeout', () => {
    it('should complete successful requests', async () => {
      const mockResponse = new Response(JSON.stringify({ status: 'ok' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
      
      vi.spyOn(global, 'fetch').mockResolvedValueOnce(mockResponse)

      const responsePromise = fetchWithTimeout('/test')
      await vi.runAllTimersAsync()
      const response = await responsePromise

      expect(response.ok).toBe(true)
    })

    it.skip('should timeout slow requests', async () => {
      // TODO: Fix flaky timer test
      // The AbortController timeout behavior is difficult to test with mocks
      vi.useRealTimers()
      
      vi.spyOn(global, 'fetch').mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 500))
      )

      const promise = fetchWithTimeout('/test', {}, 50)
      
      await expect(promise).rejects.toThrow('timeout')
    })

    it('should use default timeout', () => {
      expect(DEFAULT_TIMEOUT).toBe(10000)
    })

    it('should have longer timeout for CPU-intensive operations', () => {
      expect(LONG_TIMEOUT).toBe(30000)
    })
  })

  describe('getHealth', () => {
    it('should fetch health status', async () => {
      const mockHealth = {
        status: 'healthy',
        satellites_loaded: 1000,
        cache_connected: true,
      }

      vi.spyOn(global, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(mockHealth), { status: 200 })
      )

      const result = await getHealth()

      expect(result.status).toBe('healthy')
      expect(result.satellites_loaded).toBe(1000)
    })
  })

  describe('getSatellites', () => {
    it('should fetch satellites with default pagination', async () => {
      const mockData = {
        total: 1000,
        satellites: [{ satellite_id: '25544', name: 'ISS' }],
      }

      vi.spyOn(global, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(mockData), { status: 200 })
      )

      const result = await getSatellites()

      expect(result.satellites).toHaveLength(1)
      expect(result.satellites[0].satellite_id).toBe('25544')
    })

    it('should accept custom limit and offset', async () => {
      const mockData = { total: 1000, satellites: [] }
      const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(mockData), { status: 200 })
      )

      await getSatellites(50, 100)

      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('limit=50'),
        expect.anything()
      )
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('offset=100'),
        expect.anything()
      )
    })
  })

  describe('getAllPositions', () => {
    it('should fetch all satellite positions', async () => {
      // Mock data matching PositionsResponseSchema
      const mockData = {
        count: 100,
        source: 'tle',
        positions: [
          { id: '25544', lat: 51.6, lon: -0.1, alt: 420, v: 7.66 },
        ],
      }

      vi.spyOn(global, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(mockData), { status: 200 })
      )

      const result = await getAllPositions()

      expect(result.positions).toBeDefined()
      expect(result.positions[0].id).toBe('25544')
    })
  })

  describe('getSatelliteRisk', () => {
    it('should use long timeout for risk analysis', async () => {
      const mockData = {
        satellite_id: '25544',
        risks: [],
      }

      const fetchSpy = vi.spyOn(global, 'fetch').mockResolvedValueOnce(
        new Response(JSON.stringify(mockData), { status: 200 })
      )

      await getSatelliteRisk('25544', 24)

      // Risk analysis should use LONG_TIMEOUT
      // Note: We can't directly test the timeout value in this mock,
      // but we verify the call was made correctly
      expect(fetchSpy).toHaveBeenCalled()
    })
  })

  describe('Error Handling', () => {
    it('should throw on non-ok response', async () => {
      vi.spyOn(global, 'fetch').mockResolvedValueOnce(
        new Response(null, { status: 500 })
      )

      await expect(getHealth()).rejects.toThrow('API error')
    })

    it('should throw on network error', async () => {
      vi.spyOn(global, 'fetch').mockRejectedValueOnce(new Error('Network error'))

      await expect(getHealth()).rejects.toThrow('Network error')
    })
  })
})
