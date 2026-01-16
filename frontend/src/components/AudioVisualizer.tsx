import React from 'react'
import './AudioVisualizer.css'

interface AudioVisualizerProps {
  isRecording: boolean
  isProcessing: boolean
}

export default function AudioVisualizer({ isRecording, isProcessing }: AudioVisualizerProps) {
  return (
    <div className="audio-visualizer">
      {isRecording && (
        <div className="waveform">
          {Array.from({ length: 20 }).map((_, i) => (
            <div
              key={i}
              className="wave-bar"
              style={{
                animationDelay: `${i * 0.1}s`,
                height: `${20 + Math.random() * 60}%`
              }}
            />
          ))}
        </div>
      )}
      {isProcessing && (
        <div className="processing-indicator">Processing audio...</div>
      )}
    </div>
  )
}
