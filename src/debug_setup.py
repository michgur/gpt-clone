import subprocess
import aiofiles, aiofiles.os
import arel
import htmlmin

from fastapi import APIRouter
from fastapi.templating import Jinja2Templates

router = APIRouter()

# responsibilities:
#   - setup hot reloading
#   - run tailwindcss
#   - minify html


async def run_tailwindcss():
    subprocess.run(
        [
            "npx",
            "tailwindcss",
            "-i",
            "./styles/app.css",
            "-o",
            "../static/app.css",
            "--minify",
        ],
        cwd="./tailwind",
    )


async def minify_templates():
    for fn in await aiofiles.os.listdir("./templates"):
        async with aiofiles.open(f"./templates/{fn}", "r") as f:
            template = await f.read()
        async with aiofiles.open(f"./templates-min/{fn}", "w") as f:
            await f.write(
                htmlmin.minify(
                    template,
                    remove_all_empty_space=True,
                    remove_comments=True,
                    reduce_empty_attributes=False,
                    remove_optional_attribute_quotes=False,
                    convert_charrefs=False,
                )
            )


hotreload = arel.HotReload(
    paths=[
        arel.Path("./templates", on_reload=[run_tailwindcss, minify_templates]),
        arel.Path("./static"),
    ],
)

# setup hot-reload route
router.add_websocket_route("/hot-reload", endpoint=hotreload, name="hot-reload")
router.add_event_handler("startup", hotreload.startup)
router.add_event_handler("shutdown", hotreload.shutdown)


def apply_globals(templates: Jinja2Templates):
    templates.env.globals["DEBUG"] = True
    templates.env.globals["hotreload"] = hotreload
