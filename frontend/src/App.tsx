import React, { useState } from 'react'
import VoiceChat from './components/VoiceChat'
import TextInput from './components/TextInput'
import './App.css'

function App() {
  const [inputMode, setInputMode] = useState<'voice' | 'text'>('voice')

  return (
    <div className="app">
      <header className="app-header">
        <h1>Agentic Assistant</h1>
        <button
          className="mode-toggle"
          onClick={() => setInputMode(inputMode === 'voice' ? 'text' : 'voice')}
          title={`Switch to ${inputMode === 'voice' ? 'text' : 'voice'} mode`}
        >
          {inputMode === 'voice' ? '⌨️' : '🎤'}
        </button>
      </header>
      
      <main className="app-main">
        {inputMode === 'voice' ? (
          <VoiceChat />
        ) : (
          <TextInput />
        )}
      </main>
    </div>
  )
}

export default App
