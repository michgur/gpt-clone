import os
from typing import Generator
from model import Chat
import aiofiles, aiofiles.os


path = "./chat_db"


async def read(chat_id: str) -> Chat:
    async with aiofiles.open(f"{path}/{chat_id}.json", "r") as f:
        chat = Chat.model_validate_json(await f.read())
    return chat


async def read_all() -> list[Chat]:
    chats = []
    for fn in await aiofiles.os.listdir(path):
        async with aiofiles.open(f"{path}/{fn}", "r") as f:
            chats.append(Chat.model_validate_json(await f.read()))
    return chats


async def write(chat: Chat, field: str = None):
    if field is not None:
        try:
            existing_chat = await read(chat.id)
            setattr(existing_chat, field, getattr(chat, field))
            chat = existing_chat
        except FileNotFoundError:
            pass
    async with aiofiles.open(f"{path}/{chat.id}.json", "w") as f:
        await f.write(chat.model_dump_json())


async def delete(chat_id: str):
    await aiofiles.os.remove(f"{path}/{chat_id}.json")


async def delete_all():
    for fn in await aiofiles.os.listdir(path):
        await aiofiles.os.remove(f"{path}/{fn}")
