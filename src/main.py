import os
# if no env variables - use dotenv
if "DEBUG" not in os.environ:
    import dotenv
    dotenv.load_dotenv()

import asyncio
from collections import defaultdict
from typing import Annotated, Optional
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from model import Chat, Message
import chat_db
import gpt

# TODO: replace chat_db with actual database
# TODO: replace buffer with actual message queue
# TODO: connect to actual assistant
# TODO: host on actual server


DEBUG = os.environ.get("DEBUG", "false").lower() == "true"


app = FastAPI()

app.mount("/static", StaticFiles(directory="./static"), name="static")
app.add_middleware(GZipMiddleware, minimum_size=1000)

templates = Jinja2Templates("./templates-min")


@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/chats/welcome")
async def read_welcome_screen(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})


@app.delete("/chats/all")
async def delete_chat_all(request: Request):
    asyncio.create_task(chat_db.delete_all())
    # return empty HTML
    return HTMLResponse()


@app.get("/chats/all")
async def read_chat_all(request: Request, select: Optional[str] = None):
    chats = list(await chat_db.read_all())

    # sort chats from newest to oldest
    chats.sort(key=lambda x: x.created_at, reverse=True)
    return templates.TemplateResponse(
        "chat-list.html", {"request": request, "chats": chats, "selected": select}
    )


@app.get("/chat/{id}")
async def read_chat(request: Request, id: str):
    # open JSON file in ./chat_db
    chat = await chat_db.read(id)
    # if this is an htmx request, return partial template
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "chat.html", {"request": request, "chat": chat}
        )
    # otherwise, return full template
    return templates.TemplateResponse("index.html", {"request": request, "chat": chat})


buffer: dict[str, list[ServerSentEvent]] = defaultdict(list)


from time import time


async def generate_response(chat: Chat):
    message = chat.messages[-1]

    t = time()
    async for block in gpt.chat_completion(chat):
        message.content += block
        # buffer block to be sent to client
        buffer[chat.id].append(
            ServerSentEvent(f"<span>{block}</span>", event="content")
        )
        # update db to reflect new content
        _t = time()
        if _t - t > 0.2:
            asyncio.create_task(chat_db.write(chat, "messages"))
            t = _t

    message.finished = True
    buffer[chat.id].append(
        ServerSentEvent(
            '<div hx-swap-oob="outerHTML" id="sse-listener" class=""></div>', event="done"
        )
    )
    asyncio.create_task(chat_db.write(chat, "messages"))


async def read_response_from_buffer(chat_id: str):
    global buffer
    while True:
        if buffer[chat_id]:
            sse = buffer[chat_id].pop(0)
            yield sse
            if sse.event == "done":
                break
        else:
            await asyncio.sleep(0.1)


async def send_message(chat: Chat, content: str):
    message = Message(role="user", content=content.strip())
    response = Message(role="assistant", finished=False)
    chat.messages.extend([message, response])
    asyncio.create_task(generate_response(chat))
    await chat_db.write(chat, "messages")


@app.post("/chats/new")
async def create_chat(request: Request, message: Annotated[str, Form()]):
    # create new chat object
    chat = Chat(name=None)
    await send_message(chat, message)

    return templates.TemplateResponse(
        "chat-list-item.html", {"request": request, "chat": chat, "is_selected": True}
    )


@app.post("/chat/{id}")
async def create_message(request: Request, id: str, message: Annotated[str, Form()]):
    # open JSON file in ./chat_db
    chat = await chat_db.read(id)
    await send_message(chat, message)

    return templates.TemplateResponse(
        "message-and-response.html", {"request": request, "chat": chat}
    )


@app.get("/chat/{id}/rename")
async def rename_chat(request: Request, id: str):
    # open JSON file in ./chat_db
    chat = await chat_db.read(id)
    chat.name = await gpt.generate_name(chat)
    # sleep 1 s
    await asyncio.sleep(1)
    # update JSON file in ./chat_db
    asyncio.create_task(chat_db.write(chat, "name"))

    return HTMLResponse(chat.name)


# streaming responses require no middleware
# therefore, we need the main app to have no middleware
sse_app = FastAPI()


@sse_app.get("/chat/{id}/sse")
async def recieve_message(request: Request, id: str):
    return EventSourceResponse(read_response_from_buffer(id))


if DEBUG:
    import debug_setup

    sse_app.include_router(debug_setup.router, prefix="/debug")
    debug_setup.apply_globals(templates)

sse_app.mount("/", app)
sse_app.openapi().update(app.openapi())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:sse_app", reload=True)
