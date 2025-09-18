import uvicorn
from fastapi import FastAPI
from heygen_routes.routes import router 

app = FastAPI()
app.include_router(router, prefix="/heygen")

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)

