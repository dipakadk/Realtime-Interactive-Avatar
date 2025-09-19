import os
import httpx
from fastapi import APIRouter,Request,HTTPException
from fastapi.responses import JSONResponse,HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import WebSocket
import websocket as ws_client
import asyncio
import queue
import threading
import json
import httpx
from services import KB_PROMPT
from dotenv import load_dotenv
load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise RuntimeError("Please set DEEPGRAM_API_KEY in .env")

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
if not HEYGEN_API_KEY:
    raise RuntimeError("Please set HEYGEN_API_KEY in .env")

HEYGEN_SERVER_URL = os.getenv("HEYGEN_SERVER_URL")
if not HEYGEN_SERVER_URL:
    raise RuntimeError("Please set HEYGEN_SERVER_URL as https://api.heygen.com in .env")
HEADERS_HEYGEN = {"Content-Type": "application/json", "X-Api-Key": HEYGEN_API_KEY}
DG_URL = "wss://api.deepgram.com/v1/listen?model=nova-2&encoding=linear16&sample_rate=16000"
HEADERS_DG = [f"Authorization: Token {DEEPGRAM_API_KEY}"]



KB_NAME = "Conversation Knowledge Base"
KB_OPENING = "Hello! How can I assist you today?"
# _KB_ID = "776202c4fd304d2d8321ec58b8bfb0eb"
_KB_ID = None

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/generate_knowledge_base_id",tags=["Generate Knowledge Base ID"])
async def ensure_kb_id() -> str:
    global _KB_ID
    if _KB_ID:
        return _KB_ID

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            list_resp = await client.get(
                f"{HEYGEN_SERVER_URL}/v1/streaming/knowledge_base/list",
                headers=HEADERS_HEYGEN,
            )
            list_resp.raise_for_status()
            for kb in list_resp.json().get("data", []):
                if kb.get("name") == KB_NAME:
                    _KB_ID = kb["id"]
                    return _KB_ID
        except Exception:
            pass

        resp = await client.post(
            f"{HEYGEN_SERVER_URL}/v1/streaming/knowledge_base/create",
            headers=HEADERS_HEYGEN,
            json={"name": KB_NAME, "opening": KB_OPENING, "prompt": KB_PROMPT},
        )
        resp.raise_for_status()
        _KB_ID = resp.json().get("data", {}).get("id")
        return _KB_ID


@router.get("/",response_class=HTMLResponse)
async def home(request:Request):
    return templates.TemplateResponse("index.html",{"request":request})


@router.post("/api/get_token",tags=["Generate Token"])
async def get_token():
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{HEYGEN_SERVER_URL}/v1/streaming.create_token", headers= HEADERS_HEYGEN)
        r.raise_for_status()
        return JSONResponse(r.json())
    

@router.post("/api/new_session",tags=["Streaming New Session"])
async def new_session(payload:dict):
    session_token = payload.get("session_token")
    if not session_token:
        raise HTTPException(400,"Missing session_token")
    
    kd_id = await ensure_kb_id()
    body ={
        "version":"v2",
        "avatar_id":payload.get("avatar_id","default"),
        "knowledge_base_id":kd_id,
        # "stt_settings": {
        # "provider": "deepgram",
        # "confidence": 0.55
        # },
        }
    if payload.get("voice_id"):
        body["voice"] = {"voice_id":payload["vocie_id"],"emotion":"Friendly"}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{HEYGEN_SERVER_URL}/v1/streaming.new",
                                headers={"Content-Type": "application/json", "Authorization": f"Bearer {session_token}"},
                                json=body
                              )
        r.raise_for_status()
        return JSONResponse(r.json())
    
    
@router.post("/api/start_stream",tags=["Start Stream"])
async def start_stream(payload: dict):
    session_token = payload.get("session_token")
    session_id = payload.get("session_id")
    if not session_token or not session_id:
        raise HTTPException(400, "Missing session_token/session_id")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {session_token}"}
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(f"{HEYGEN_SERVER_URL}/v1/streaming.start", headers=headers, json={"session_id": session_id})
        r.raise_for_status()
        return JSONResponse(r.json())
        
        
@router.post("/api/close_session",tags=["Close Session"])
async def close_session(payload: dict):
    session_token = payload.get("session_token")
    session_id = payload.get("session_id")
    if not all([session_token, session_id]):
        raise HTTPException(400, "Missing params")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {session_token}"}
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(f"{HEYGEN_SERVER_URL}/v1/streaming.stop", headers=headers, json={"session_id": session_id})
        r.raise_for_status()
        return JSONResponse(r.json())
    
    
async def send_text_to_heygen(session_token: str, session_id: str, final_text: str):
    if not final_text.strip():
        return
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {session_token}"}
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(f"{HEYGEN_SERVER_URL}/v1/streaming.task",
                              headers=headers,
                              json={"session_id": session_id, "text": final_text, "task_type": "chat"})
        r.raise_for_status()
        return r.json()
    
    
# @router.post("/api/interrupt_task", tags=["Interrupt Task"])
# async def interrupt_task(payload: dict):
#     session_token = payload.get("session_token")
#     session_id = payload.get("session_id")
#     if not all([session_token, session_id]):
#         raise HTTPException(status_code=400, detail="Missing params")
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {session_token}"
#     }
#     async with httpx.AsyncClient(timeout=300) as client:
#         resp = await client.post(
#             f"{HEYGEN_SERVER_URL}/v1/streaming.interrupt",
#             headers=headers,
#             json={"session_id": session_id}
#         )
#         resp.raise_for_status()
#         return JSONResponse(content=resp.json())
    
    
@router.websocket("/ws/speech")
async def ws_speech(websocket: WebSocket):
    print("--------------")
    print(websocket)
    
    """
    Frontend connects here. We receive microphone audio from the frontend,
    send to Deepgram for transcription, stream partial & final transcripts back,
    and forward final transcript to HeyGen as a chat task. Keep-alive is sent
    to HeyGen to prevent avatar disappearance.
    """
    await websocket.accept()
    params = websocket.query_params
    print("====================================================")
    print(params)
    session_token = params.get("session_token")
    session_id = params.get("session_id")

    if not session_token or not session_id:
        await websocket.close(code=4001)
        return

    send_queue = queue.Queue(maxsize=1000)
    stop_flag = threading.Event()
    full_transcript = ""
    loop = asyncio.get_event_loop()

    def dg_on_open(ws):
        def pump_audio():
            while not stop_flag.is_set():
                try:
                    data = send_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if data is None:
                    break
                try:
                    ws.send(data, opcode=ws_client.ABNF.OPCODE_BINARY)
                except Exception as e:
                    print("DG send error:", e)
                    break
        threading.Thread(target=pump_audio, daemon=True).start()

    def dg_on_message(ws, message):
        print("===========",message)
        nonlocal full_transcript
        try:
            data = json.loads(message)
            alt = data.get("channel", {}).get("alternatives", [{}])[0]
            transcript = alt.get("transcript", "")
            if transcript:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"type": "partial_transcript", "text": transcript}),
                    loop,
                )
                full_transcript += transcript + " "

            if data.get("is_final"):
                final_text = full_transcript.strip()
                full_transcript = ""

                async def handle_final():
                    await websocket.send_json({"type": "final_transcript", "text": final_text})
                    # Send final text to HeyGen
                    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {session_token}"}
                    async with httpx.AsyncClient(timeout=300) as client:
                        try:
                            r = await client.post(
                                f"{HEYGEN_SERVER_URL}/v1/streaming.task",
                                headers=headers,
                                json={"session_id": session_id, "text": final_text, "task_type": "chat"},
                            )
                            r.raise_for_status()
                            await websocket.send_json({"type": "heygen_response", "data": r.json()})
                        except:
                            return "=====================Here i got an error===================="
                asyncio.run_coroutine_threadsafe(handle_final(), loop)
        except Exception as e:
            print("DG on_message error:", e)

    def dg_on_error(ws, error):
        print("DG WS error:", error)

    def dg_on_close(ws, code, reason):
        print("DG WS closed:", code, reason)

    dg_ws_app = ws_client.WebSocketApp(
        DG_URL,
        header=HEADERS_DG,
        on_open=dg_on_open,
        on_message=dg_on_message,
        on_error=dg_on_error,
        on_close=dg_on_close,
    )
    threading.Thread(target=dg_ws_app.run_forever, daemon=True).start()

    async def heygen_keep_alive():
        url = f"{HEYGEN_SERVER_URL}/v1/streaming.keep_alive"
        headers = {"Authorization": f"Bearer {session_token}", "Content-Type": "application/json"}
        data = {"session_id": session_id}
        while True:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, headers=headers, json=data, timeout=10)
                    resp.raise_for_status()
                    print("[Keep-Alive] Success")
            except Exception as e:
                print("[Keep-Alive] Failed:", e)
            await asyncio.sleep(300)

    asyncio.create_task(heygen_keep_alive())

    # ---------------- Receive audio from frontend ----------------
    try:
        while True:
            audio_bytes = await websocket.receive_bytes()
            send_queue.put(audio_bytes)
    except Exception:
        stop_flag.set()
        send_queue.put(None)
        dg_ws_app.close()
        await websocket.close()
