from model import Chat
import openai

API_KEY = "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"

openai = openai.AsyncClient(api_key=API_KEY)


async def chat_completion(chat: Chat):
    messages = [
        {"role": m.role, "content": m.content} for m in chat.messages if m.finished
    ]
    completion = await openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        stream=True,
    )

    partial: openai.ChatCompletionChunk
    async for partial in completion:
        delta = partial.choices[0].delta
        if delta.content:
            yield delta.content


async def generate_name(chat: Chat):
    chat_str = "\n".join(
        [f"{m.role}: {m.content}" for m in chat.messages if m.finished]
    )
    messages = [
        {
            "role": "system",
            "content": "You are a chat title generator. You reply with only the title, no other text.",
        },
        {
            "role": "user",
            "content": f"Generate a short and catchy title (2-6 words) for the following chat:\n\n{chat_str}\n\nShort Title:",
        },
    ]

    completion = await openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
    )
    title = completion.choices[0].message.content
    # if title is surrounded by quotes, remove them
    if title.startswith('"') and title.endswith('"'):
        title = title[1:-1]
    return title
