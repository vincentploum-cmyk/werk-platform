"""Hello World API endpoint — simple greeting for integration testing."""

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/hello")
async def say_hello(name: str = Query("World", description="Name to greet")):
    """Return a friendly greeting. Used for full-stack integration testing."""
    return {"message": f"Hello, {name}!"}