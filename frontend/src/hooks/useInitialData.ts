/**
 * Custom hook for batched initial data fetching.
 * 
 * Story 2.1 (P0-1): Batch API Calls
 * 
 * Fetches positions, health, and launches in parallel using Promise.all()
 * to reduce initial page load time from ~1200ms to ~400ms (3x faster).
 * 
 * Usage:
 * ```tsx
 * const { data, isLoading, error } = useInitialData()
 * 
 * if (isLoading) return <Skeleton />
 * if (error) return <Error message={error.message} />
 * 
 * const { positions, health, launches } = data
 * ```
 */

import { useQuery } from '@tanstack/react-query'
import { getInitialData } from '@/services/api'

export function useInitialData() {
  return useQuery({
    queryKey: ['initial-data'],
    queryFn: getInitialData,
    staleTime: 30000, // 30 seconds
    retry: 2,
  })
}
