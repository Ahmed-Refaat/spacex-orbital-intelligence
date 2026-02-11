import { useEffect, useRef, useCallback } from 'react'
import { useStore } from '@/stores/useStore'
import type { WSMessage } from '@/types'

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/positions`

// Exponential backoff config
const INITIAL_RETRY_DELAY = 1000  // 1s
const MAX_RETRY_DELAY = 30000      // 30s
const BACKOFF_MULTIPLIER = 1.5

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>()
  const retryDelayRef = useRef<number>(INITIAL_RETRY_DELAY)
  const { updateSatellites, setWsConnected, setSelectedSatelliteDetail, selectedSatelliteId } = useStore()

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    console.log('Connecting to WebSocket...')
    const ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      console.log('WebSocket connected')
      setWsConnected(true)
      // Reset retry delay on successful connection
      retryDelayRef.current = INITIAL_RETRY_DELAY
    }

    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)

        switch (message.type) {
          case 'positions':
            updateSatellites(message.data)
            break
          case 'satellite':
            if (message.data.satellite_id === selectedSatelliteId) {
              setSelectedSatelliteDetail(message.data)
            }
            break
          case 'ping':
            ws.send(JSON.stringify({ type: 'pong' }))
            break
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected, will retry...')
      setWsConnected(false)
      wsRef.current = null

      // Exponential backoff for reconnection
      const currentDelay = retryDelayRef.current
      console.log(`Reconnecting in ${currentDelay}ms...`)
      
      reconnectTimeoutRef.current = setTimeout(() => {
        connect()
      }, currentDelay)

      // Increase delay for next retry (up to max)
      retryDelayRef.current = Math.min(
        currentDelay * BACKOFF_MULTIPLIER,
        MAX_RETRY_DELAY
      )
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      // Error is handled by onclose
    }

    wsRef.current = ws
  }, [updateSatellites, setWsConnected, setSelectedSatelliteDetail, selectedSatelliteId])

  const disconnect = useCallback(() => {
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = undefined
    }
    
    // Close WebSocket
    if (wsRef.current) {
      // Remove handlers to prevent reconnection
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
    
    // Reset retry delay
    retryDelayRef.current = INITIAL_RETRY_DELAY
  }, [])

  const subscribeSatellite = useCallback((satelliteId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        satellite_id: satelliteId
      }))
    }
  }, [])

  useEffect(() => {
    connect()
    
    // Cleanup on unmount
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  // Subscribe to selected satellite
  useEffect(() => {
    if (selectedSatelliteId) {
      subscribeSatellite(selectedSatelliteId)
    }
  }, [selectedSatelliteId, subscribeSatellite])

  return {
    connected: wsRef.current?.readyState === WebSocket.OPEN,
    connect,
    disconnect,
    subscribeSatellite
  }
}
