# Multi-Agent AI System

Production-grade multi-agent AI platform with plugin-based modular architecture.

## Features

- **Plugin-based Architecture**: Every component is a swappable plugin
- **Swarm Intelligence**: Fast, specialized micro-agents
- **Adaptive LLM Council**: Democratic reasoning only when needed (60-70% compute reduction)
- **Multimodal Intelligence**: Text, audio, image, and video processing
- **Humanized Interaction**: ChatGPT-like warmth and flow
- **Cost-Aware Orchestration**: Intelligent model selection & VRAM governance
- **Voice-First Desktop App**: Tauri + React + TypeScript with native audio

## Architecture

- **Backend**: FastAPI (async/await) with Hugging Face models
- **Frontend**: Tauri + React + TypeScript desktop app
- **Plugin System**: Auto-discovery, dependency injection, hot-reloading
- **VRAM Management**: Automatic model eviction (soft: 85%, hard: 92%)

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn api.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run tauri:dev
```

## Configuration

Edit `backend/config.yaml` to configure:
- VRAM limits
- Model settings
- Plugin enable/disable
- Council thresholds
- Memory settings

## Plugins

All plugins are in `backend/plugins/`:
- **Input**: text, audio (STT), image, video
- **Cognitive**: intent, complexity, NER, embeddings, semantic search, SQL
- **Reasoning**: Phi (always), Qwen (on-demand), council coordinator
- **Memory**: vector memory, confidence decay
- **Humanization**: Phi-based style matching
- **Output**: text streaming, audio TTS

## License

MIT
