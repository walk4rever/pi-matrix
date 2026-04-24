from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import devices, memory, config, feishu, auth, dashboard

app = FastAPI(title="pi-matrix API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(memory.router)
app.include_router(config.router)
app.include_router(feishu.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"ok": True}
