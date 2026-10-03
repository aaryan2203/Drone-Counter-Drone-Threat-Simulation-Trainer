"""
FastAPI Main Application Entrypoint for Drone Threat Simulation Trainer.
Coordinates REST APIs, WebSockets, SQLite database lifecycle, and CORS.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.endpoints import router as api_router
from .api.websocket import router as ws_router
from .database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes SQLite database tables on startup."""
    init_db()
    yield


app = FastAPI(
    title="AI Drone & Counter-Drone Threat Simulation Trainer",
    description="Backend API supporting perception events, procedural scenarios, trainee interaction, and AAR reporting.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local training dashboards (React / Next.js) and desktop clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST endpoints and WebSocket router
app.include_router(api_router)
app.include_router(ws_router)

# Mount Dashboard static frontend for offline / browser access
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dashboard_public_dir = os.path.join(PROJECT_ROOT, "dashboard", "public")

if os.path.exists(dashboard_public_dir):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    app.mount("/dashboard", StaticFiles(directory=dashboard_public_dir, html=True), name="dashboard")

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return FileResponse(os.path.join(dashboard_public_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
