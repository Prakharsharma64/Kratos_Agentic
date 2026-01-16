const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  async chat(request: { message: string; request_type: string; metadata?: any }) {
    const response = await fetch(`${this.baseUrl}/api/chat/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`)
    }

    return response.json()
  }

  async transcribeAudio(audioFile: File) {
    const formData = new FormData()
    formData.append('file', audioFile)

    const response = await fetch(`${this.baseUrl}/api/audio/transcribe`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`)
    }

    return response.json()
  }

  async getHealth() {
    const response = await fetch(`${this.baseUrl}/api/health/`)
    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`)
    }
    return response.json()
  }

  async getPlugins() {
    const response = await fetch(`${this.baseUrl}/api/plugins/`)
    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`)
    }
    return response.json()
  }
}

export const apiClient = new ApiClient()
