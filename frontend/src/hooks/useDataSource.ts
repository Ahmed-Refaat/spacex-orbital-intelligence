import { useQuery } from '@tanstack/react-query'

export interface DataSourceStatus {
  current_source: 'tle' | 'omm'
  available_sources: string[]
  satellite_count: number
  last_update: string
  auto_refresh: boolean
}

async function fetchDataSource(): Promise<DataSourceStatus> {
  const response = await fetch('/api/v1/data-source')
  if (!response.ok) {
    throw new Error('Failed to fetch data source')
  }
  return response.json()
}

export function useDataSource() {
  const { data, isLoading, error } = useQuery<DataSourceStatus>({
    queryKey: ['data-source'],
    queryFn: fetchDataSource,
    refetchInterval: 10000, // Refresh every 10 seconds
    retry: 3,
  })

  // Format source name for display
  const getSourceLabel = (source: string, count: number) => {
    const sourceNames: Record<string, string> = {
      tle: 'Space-Track.org',
      omm: 'OMM Format',
    }
    return `${sourceNames[source] || source} (${count.toLocaleString()} satellites)`
  }

  return {
    source: data?.current_source || 'tle',
    satelliteCount: data?.satellite_count || 0,
    isLoading,
    error,
    sourceLabel: data 
      ? getSourceLabel(data.current_source, data.satellite_count)
      : 'Loading data source...',
    lastUpdate: data?.last_update,
  }
}
