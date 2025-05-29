"""
Simplified main.py for testing purposes.
"""
from fastapi import FastAPI

# Simple FastAPI app for testing
app = FastAPI(
    title="Test API",
    description="Simple API for testing",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Test API is running"}
