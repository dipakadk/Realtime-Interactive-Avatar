import os
import httpx
from fastapi import APIRouter
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
_KB_ID = None

router = APIRouter()

@router.post("/generate_knowledge_base_id",tags=["Generate Knowledge Base ID"])
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

