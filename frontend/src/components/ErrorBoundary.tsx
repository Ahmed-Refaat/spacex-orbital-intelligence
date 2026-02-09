/**
 * Error Boundary component for graceful error handling.
 * 
 * Story 2.3 (P0-5): Add Error Boundary
 * 
 * Catches React errors (especially Three.js crashes) and shows fallback UI
 * instead of white screen of death.
 * 
 * Usage:
 * ```tsx
 * <ErrorBoundary>
 *   <Globe />
 * </ErrorBoundary>
 * ```
 * 
 * Custom fallback:
 * ```tsx
 * <ErrorBoundary fallback={<CustomError />}>
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 */

import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = {
    hasError: false,
    error: null,
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('React Error Boundary caught:', error, errorInfo)
    
    // TODO: Send to error tracking service (e.g., Sentry)
    // logErrorToService(error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default fallback UI
      return (
        <div className="flex items-center justify-center h-screen bg-spacex-dark">
          <div className="text-center glass p-8 rounded-xl max-w-md">
            <div className="text-6xl mb-4">🛸</div>
            
            <h2 className="text-2xl font-bold text-red-400 mb-4">
              Visualization Error
            </h2>
            
            <p className="text-gray-400 mb-2">
              The 3D globe encountered an error
            </p>
            
            {this.state.error && (
              <details className="text-left text-xs text-gray-500 mb-4 mt-4">
                <summary className="cursor-pointer hover:text-gray-300">
                  Technical details
                </summary>
                <pre className="mt-2 p-2 bg-black/30 rounded overflow-auto max-h-32">
                  {this.state.error.toString()}
                </pre>
              </details>
            )}
            
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
            >
              Reload Application
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
