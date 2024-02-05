import minify_html
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request


class MinifyHTMLMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if response.headers["content-type"] == "text/html; charset=utf-8":
            if hasattr(response, "body"):
                response.body = minify_html.minify(
                    response.body.decode("utf-8")
                ).encode("utf-8")
            elif hasattr(response, "body_iterator"):
                response.body_iterator = minify_iterator(response.body_iterator)
        return response


async def minify_iterator(body_iterator):
    async for chunk in body_iterator:
        if chunk:
            yield chunk
            print(chunk)
            yield minify_html.minify(
                chunk.decode("utf-8"),
                preserve_brace_template_syntax=True,
            ).encode("utf-8")
