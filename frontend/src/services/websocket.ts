import type { StreamingChunk } from '../types'

export class WebSocketManager {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  constructor(url: string) {
    this.url = url
  }

  connect(onMessage: (chunk: StreamingChunk) => void, onError?: (error: Error) => void): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          this.reconnectAttempts = 0
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const chunk = JSON.parse(event.data) as StreamingChunk
            onMessage(chunk)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onerror = (error) => {
          if (onError) {
            onError(new Error('WebSocket error'))
          }
        }

        this.ws.onclose = () => {
          this.ws = null
          this.attemptReconnect(onMessage, onError)
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  private attemptReconnect(onMessage: (chunk: StreamingChunk) => void, onError?: (error: Error) => void) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      if (onError) {
        onError(new Error('Max reconnection attempts reached'))
      }
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    setTimeout(() => {
      this.connect(onMessage, onError).catch((error) => {
        if (onError) {
          onError(error)
        }
      })
    }, delay)
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      throw new Error('WebSocket is not connected')
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

export const wsManager = new WebSocketManager(WS_URL)
