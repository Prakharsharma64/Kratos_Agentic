import React, { useState, useEffect, useRef } from 'react'
import { wsManager } from '../services/websocket'
import { audioService } from '../services/audio'
import { apiClient } from '../services/api'
import MessageList from './MessageList'
import AudioRecorder from './AudioRecorder'
import AudioVisualizer from './AudioVisualizer'
import CouncilVisualization from './CouncilVisualization'
import type { Message, StreamingChunk, CouncilUpdate } from '../types'
import './VoiceChat.css'

export default function VoiceChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentResponse, setCurrentResponse] = useState('')
  const [councilUpdate, setCouncilUpdate] = useState<CouncilUpdate | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    // Connect WebSocket
    wsManager.connect(
      (chunk: StreamingChunk) => {
        handleStreamingChunk(chunk)
      },
      (error) => {
        console.error('WebSocket error:', error)
        setIsConnected(false)
      }
    ).then(() => {
      setIsConnected(true)
    })

    return () => {
      wsManager.disconnect()
    }
  }, [])

  const handleStreamingChunk = (chunk: StreamingChunk) => {
    switch (chunk.type) {
      case 'text':
        setCurrentResponse(prev => prev + (chunk.content as string))
        break
      case 'audio':
        audioService.playAudio(chunk.content as ArrayBuffer)
        break
      case 'council_update':
        setCouncilUpdate(chunk.content as CouncilUpdate)
        break
      case 'done':
        if (currentResponse) {
          addMessage('assistant', currentResponse)
          setCurrentResponse('')
        }
        setCouncilUpdate(null)
        setIsProcessing(false)
        break
      case 'error':
        console.error('Streaming error:', chunk.content)
        setIsProcessing(false)
        break
    }
  }

  const addMessage = (role: 'user' | 'assistant', content: string) => {
    const message: Message = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
      metadata: councilUpdate ? { council: councilUpdate } : undefined
    }
    setMessages(prev => [...prev, message])
  }

  const handleRecordingStart = async () => {
    try {
      await audioService.startRecording()
      setIsRecording(true)
    } catch (error) {
      console.error('Failed to start recording:', error)
    }
  }

  const handleRecordingStop = async () => {
    try {
      const audioBlob = await audioService.stopRecording()
      setIsRecording(false)
      setIsProcessing(true)

      // Transcribe
      const transcription = await apiClient.transcribeAudio(
        new File([audioBlob], 'recording.wav', { type: 'audio/wav' })
      )

      // Add user message
      addMessage('user', transcription.text)

      // Send to backend via WebSocket
      wsManager.send({
        request_type: 'audio',
        content: transcription.text,
        metadata: {}
      })
    } catch (error) {
      console.error('Failed to process recording:', error)
      setIsProcessing(false)
    }
  }

  return (
    <div className="voice-chat">
      <div className="voice-chat-header">
        <div className="connection-status">
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`} />
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
      </div>

      <MessageList messages={messages} />

      {councilUpdate && (
        <CouncilVisualization council={councilUpdate} />
      )}

      <div className="voice-chat-footer">
        <AudioVisualizer isRecording={isRecording} isProcessing={isProcessing} />
        
        <AudioRecorder
          isRecording={isRecording}
          isProcessing={isProcessing}
          onStart={handleRecordingStart}
          onStop={handleRecordingStop}
        />
      </div>
    </div>
  )
}
