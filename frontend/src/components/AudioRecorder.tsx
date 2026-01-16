import React from 'react'
import './AudioRecorder.css'

interface AudioRecorderProps {
  isRecording: boolean
  isProcessing: boolean
  onStart: () => void
  onStop: () => void
}

export default function AudioRecorder({
  isRecording,
  isProcessing,
  onStart,
  onStop
}: AudioRecorderProps) {
  return (
    <div className="audio-recorder">
      <button
        className={`record-button ${isRecording ? 'recording' : ''} ${isProcessing ? 'processing' : ''}`}
        onClick={isRecording ? onStop : onStart}
        disabled={isProcessing}
      >
        {isProcessing ? '⏳' : isRecording ? '⏹️' : '🎤'}
      </button>
      <div className="record-status">
        {isProcessing ? 'Processing...' : isRecording ? 'Recording...' : 'Click to record'}
      </div>
    </div>
  )
}
