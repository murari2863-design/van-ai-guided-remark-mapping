from fastapi import APIRouter

from server.classes.api_classes import HelloWorldRead

router = APIRouter(
    prefix="/api/helloworld",
    tags=["users"],
)

# --- User API Endpoints ---
@router.get("", response_model=HelloWorldRead, tags=["users"])
async def read_protected_data():
    return {"message": "Hello World!"}
