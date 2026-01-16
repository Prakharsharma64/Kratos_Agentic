import React from 'react'
import type { Message } from '../types'
import './MessageList.css'

interface MessageListProps {
  messages: Message[]
}

export default function MessageList({ messages }: MessageListProps) {
  return (
    <div className="message-list">
      {messages.map((message) => (
        <div key={message.id} className={`message message-${message.role}`}>
          <div className="message-content">{message.content}</div>
          <div className="message-timestamp">
            {message.timestamp.toLocaleTimeString()}
          </div>
        </div>
      ))}
    </div>
  )
}
