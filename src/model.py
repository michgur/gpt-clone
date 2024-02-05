from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import random


class Message(BaseModel):
    role: str
    content: str = ""
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    finished: bool = True


class Chat(BaseModel):
    id: str = Field(default_factory=lambda: str(random.randint(0, 100000)))
    name: Optional[str]
    messages: list[Message] = []
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
