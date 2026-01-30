from pydantic import BaseModel


# --- Pydantic Models for User ---
class HelloWorldRead(BaseModel):
    message: str
