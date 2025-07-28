import functools
from mimetypes import types_map as mimetype_map

import ssg.build as build
import ssg.constants as consts

import minify
from quart import Quart, Response, websocket
from watchfiles import awatch

app = Quart(__name__)
builder = build.Builder(live=True)

with open(consts.SRC_DIR / "reload.js") as file:
    RELOAD_SCRIPT = "<script>" + \
                    minify.string(mimetype_map['.js'], file.read()) + \
                    "</script>"


async def reload_on_changes():
    async for changes in awatch(consts.CONTENT_DIR, consts.SRC_DIR):
        for change_type, file_path in changes:
            if file_path == str(consts.CONTENT_DIR / "config.toml"):
                builder.load_config()

        await websocket.send("reload")


def inject_js_reloader(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        html: str = await func(*args, **kwargs)
        html += RELOAD_SCRIPT
        return html

    return wrapper


@app.route("/")
@inject_js_reloader
async def home():
    return builder.build_home()


@app.route("/blog")
@inject_js_reloader
async def blog():
    return builder.build_blog()


@app.route("/ws")
async def ws_healthcheck():
    return Response(status=200)


@app.websocket("/ws")
async def ws():
    await websocket.accept()
    await reload_on_changes()


def run(host="0.0.0.0", port=5000, minified=False):
    builder.minified = minified

    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    run()
