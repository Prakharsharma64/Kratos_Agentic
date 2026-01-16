import { useState, useEffect, useCallback } from 'react'
import { wsManager } from '../services/websocket'
import type { StreamingChunk } from '../types'

export function useWebSocket(url?: string) {
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const connect = useCallback((onMessage: (chunk: StreamingChunk) => void) => {
    const manager = url ? new (wsManager.constructor as any)(url) : wsManager
    
    manager.connect(
      (chunk) => {
        onMessage(chunk)
      },
      (err) => {
        setError(err)
        setIsConnected(false)
      }
    ).then(() => {
      setIsConnected(true)
      setError(null)
    })
  }, [url])

  const send = useCallback((data: any) => {
    const manager = url ? new (wsManager.constructor as any)(url) : wsManager
    manager.send(data)
  }, [url])

  const disconnect = useCallback(() => {
    const manager = url ? new (wsManager.constructor as any)(url) : wsManager
    manager.disconnect()
    setIsConnected(false)
  }, [url])

  return {
    isConnected,
    error,
    connect,
    send,
    disconnect
  }
}
