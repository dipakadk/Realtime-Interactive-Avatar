import uvicorn
from fastapi import FastAPI
from heygen_routes.routes import router as heygen_router

app = FastAPI()
app.include_router(heygen_router, prefix="/heygen")

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)

