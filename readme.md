Here’s your updated **README.md** with the workflow diagram included under a new **Workflow** section:

````markdown
# HeyGen Streaming with Live Audio Input

This repository demonstrates a **real-time audio streaming system** using FastAPI, Deepgram for realtime speech-to-text (STT), HeyGen for avatar streaming, and LiveKit for WebRTC audio/video streaming. Users can interact with avatars in real-time using their microphone.

---

## Features

- Real-time microphone audio capture in browser
- Streaming audio to Deepgram for live transcription
- Partial and final transcripts sent back to frontend
- Automatic submission of transcripts to HeyGen for avatar response
- LiveKit integration for video/audio streaming
- Session management with HeyGen knowledge base (KB)
- Optional voice selection for avatar responses

---

## Tech Stack

- **Backend:** FastAPI, httpx, websocket-client
- **Frontend:** HTML + JavaScript, TailwindCSS, LiveKit Client
- **Speech-to-Text:** Deepgram API
- **Avatar Streaming:** HeyGen API
- **Real-time Audio/Video:** LiveKit WebRTC
- **Environment Variables:** Managed with `.env`

---

## Prerequisites

- Python 3.11+
- NodeJS (for frontend if building further)
- FastAPI, uvicorn
- API keys for:
  - [Deepgram](https://developers.deepgram.com/)
  - [HeyGen](https://www.heygen.com/)
- Optional: LiveKit server or hosted LiveKit instance

---

## Setup

1. **Clone the repository**

```bash
git clone https://github.com/dipakadk/Realtime-Interactive-Avatar.git
cd Realtime-Interactive-Avatar
````

2. **Install Python dependencies**

```bash
pip install -r requirements.txt
```

3. **Create `.env` file**

```env
DEEPGRAM_API_KEY=your_deepgram_api_key
HEYGEN_API_KEY=your_heygen_api_key
HEYGEN_SERVER_URL=https://api.heygen.com
```

4. **Run FastAPI server**

```bash
uvicorn main:app --reload
```

---

## Workflow

The following diagram shows the data flow from the browser microphone to the HeyGen avatar and back:

```
[Browser Mic] --> [WebSocket] --> [FastAPI Backend] --> [Deepgram STT]
                                          |
                                          v
                                Partial / Final Transcript
                                          |
                                          v
                                  [HeyGen API Task]
                                          |
                                          v
                                 Avatar Audio/Video
                                          |
                                          v
                                [LiveKit Room Streaming]
                                          |
                                          v
                                      [Browser]
```

**Workflow Steps:**

1. **Browser** captures microphone audio and sends it via WebSocket to the backend.
2. **FastAPI Backend** forwards audio to Deepgram for real-time transcription.
3. **Deepgram STT** returns partial and final transcripts to backend.
4. Backend sends the final transcript to **HeyGen API** to generate avatar response.
5. **HeyGen API** returns avatar audio/video tracks.
6. Avatar tracks are streamed via **LiveKit** to the browser for playback.

