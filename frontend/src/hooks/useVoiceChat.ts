import { useState, useCallback } from 'react'
import { wsManager } from '../services/websocket'
import { audioService } from '../services/audio'
import type { Message, StreamingChunk } from '../types'

export function useVoiceChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)

  const startRecording = useCallback(async () => {
    try {
      await audioService.startRecording()
      setIsRecording(true)
    } catch (error) {
      console.error('Failed to start recording:', error)
    }
  }, [])

  const stopRecording = useCallback(async () => {
    try {
      const audioBlob = await audioService.stopRecording()
      setIsRecording(false)
      setIsProcessing(true)

      // TODO: Send to backend for transcription and processing
      // For now, just add a placeholder message
      const message: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: '[Audio message]',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, message])
      setIsProcessing(false)
    } catch (error) {
      console.error('Failed to stop recording:', error)
      setIsProcessing(false)
    }
  }, [])

  return {
    messages,
    isRecording,
    isProcessing,
    startRecording,
    stopRecording
  }
}
