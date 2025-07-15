"""
FastAPI application for LLM evaluation webapp.
Provides REST API endpoints for managing test cases and running evaluations.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from diting_inspect.routers import v1_router


# Initialize FastAPI app
app = FastAPI(title="LLM Evaluation API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=8000)
