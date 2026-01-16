export class AudioService {
  private mediaRecorder: MediaRecorder | null = null
  private audioChunks: Blob[] = []

  async startRecording(): Promise<void> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      this.mediaRecorder = new MediaRecorder(stream)
      this.audioChunks = []

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data)
        }
      }

      this.mediaRecorder.start()
    } catch (error) {
      throw new Error(`Failed to start recording: ${error}`)
    }
  }

  async stopRecording(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder) {
        reject(new Error('MediaRecorder not initialized'))
        return
      }

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' })
        resolve(audioBlob)
      }

      this.mediaRecorder.stop()
      this.mediaRecorder.stream.getTracks().forEach(track => track.stop())
    })
  }

  playAudio(audioData: ArrayBuffer | Blob): void {
    const audio = new Audio()
    const url = URL.createObjectURL(
      audioData instanceof Blob ? audioData : new Blob([audioData], { type: 'audio/wav' })
    )
    audio.src = url
    audio.play().catch(error => {
      console.error('Failed to play audio:', error)
    })
  }
}

export const audioService = new AudioService()
