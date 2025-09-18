import os
import httpx
from fastapi import APIRouter,Request,HTTPException
from fastapi.responses import JSONResponse,HTMLResponse
from fastapi.templating import Jinja2Templates
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
KB_NAME = "Conversation Knowledge Base"
KB_OPENING = "Hello! How can I assist you today?"
KB_PROMPT = """You are smart virtual assistant that helps the user about the medical science.
If the user provides the query outside from the medical science,just respond with sorry saying that you only helps the medical science related query in conversational way and nothing else."""
# _KB_ID = "776202c4fd304d2d8321ec58b8bfb0eb"
_KB_ID = None

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")



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


# @router.get("/",response_class=HTMLResponse)
# async def home(request:Request):
#     return templates.TemplateResponse("index.html",{"request":request})


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
    session_id = payload.get("session_id")
    session_token = payload.get("session_token")
    
    if not session_id or session_token:
        raise HTTPException(400, "Missing session_token/session_id")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {session_token}"}
    async with httpx.AsyncClient(timeout=30) as client:
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
    
@router.post("/api/interrupt_task", tags=["Interrupt Task"])
async def interrupt_task(payload: dict):
    session_token = payload.get("session_token")
    session_id = payload.get("session_id")
    if not all([session_token, session_id]):
        raise HTTPException(status_code=400, detail="Missing params")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {session_token}"
    }
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{HEYGEN_SERVER_URL}/v1/streaming.interrupt",
            headers=headers,
            json={"session_id": session_id}
        )
        resp.raise_for_status()
        return JSONResponse(content=resp.json())
    
    
