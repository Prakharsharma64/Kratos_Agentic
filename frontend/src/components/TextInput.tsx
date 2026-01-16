import React, { useState } from 'react'
import { wsManager } from '../services/websocket'
import MessageList from './MessageList'
import type { Message } from '../types'
import './TextInput.css'

export default function TextInput() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)

  const handleSend = () => {
    if (!input.trim() || isProcessing) return

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsProcessing(true)

    // Send via WebSocket
    wsManager.send({
      request_type: 'text',
      content: input,
      metadata: {}
    })
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="text-input-container">
      <MessageList messages={messages} />
      
      <div className="text-input-footer">
        <textarea
          className="text-input-field"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message... (Press Enter to send)"
          disabled={isProcessing}
          rows={3}
        />
        <button
          className="send-button"
          onClick={handleSend}
          disabled={!input.trim() || isProcessing}
        >
          Send
        </button>
      </div>
    </div>
  )
}
