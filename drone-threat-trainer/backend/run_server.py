"""
FastAPI Backend Server Runner.
Launches Uvicorn ASGI server with automatic reload for development.
"""

import os
import sys
import uvicorn

# Add project root and backend to Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)


def main():
    print("==========================================================")
    print("   AI DRONE THREAT SIMULATION TRAINER - FASTAPI BACKEND")
    print("==========================================================")
    print("API Documentation:  http://127.0.0.1:8000/docs")
    print("WebSocket Feed:     ws://127.0.0.1:8000/ws/telemetry")
    print("Health Endpoint:    http://127.0.0.1:8000/api/health")
    print("==========================================================")

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir=CURRENT_DIR
    )


if __name__ == "__main__":
    main()
