export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  metadata?: {
    council?: CouncilUpdate
    audioUrl?: string
  }
}

export interface CouncilUpdate {
  stage: 'opinions' | 'review' | 'synthesis'
  members: CouncilMember[]
  dissent?: boolean
}

export interface CouncilMember {
  id: number
  opinion: string
  score: number
  status: 'thinking' | 'complete' | 'error'
}

export interface StreamingChunk {
  type: 'text' | 'audio' | 'council_update' | 'error' | 'done'
  content: string | ArrayBuffer | CouncilUpdate
  metadata?: Record<string, any>
}

export interface ChatRequest {
  message: string
  request_type: 'text' | 'audio' | 'image' | 'video'
  metadata?: Record<string, any>
}
