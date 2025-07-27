import asyncio
import functools
from mimetypes import types_map as mimetype_map

import ssg.build as build
import ssg.constants as consts

import minify
from quart import Quart, Response, websocket
from watchfiles import awatch

MINIFIED = False

app = Quart(__name__)
env = build.make_jinja_env(live=True)


async def reload_on_changes():
    async for changes in awatch(consts.CONTENT_DIR, consts.SRC_DIR):
        for change_type, file_path in changes:
            if file_path == str(consts.CONTENT_DIR / "config.toml"):
                env.globals.update(build.load_config())

        await websocket.send("reload")


def inject_js_reloader(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        with (open(consts.SRC_DIR / "reload.js") as reload_script):
            script = "<script>" + \
                     minify.string(mimetype_map['.js'], reload_script.read()) + \
                     "</script>"

        html: str = await func(*args, **kwargs)

        if "</body>" in html:
            html = html.replace("</body>", script + "</body>")
        elif "</html>" in html:
            html = html.replace("</html>", script + "</html>")
        else:
            html = html + script

        return html

    return wrapper


@app.route("/")
@inject_js_reloader
async def home():
    return build.build_home(env, minified=MINIFIED, live=True)


@app.route("/blog")
@inject_js_reloader
async def blog():
    return build.build_blog(env, minified=MINIFIED, live=True)


@app.route("/ws")
async def ws_healthcheck():
    return Response(status=200)


@app.websocket("/ws")
async def ws():
    await websocket.accept()
    await asyncio.create_task(reload_on_changes())


def run(host="0.0.0.0", port=5000, minify=False):
    global MINIFIED
    MINIFIED = minify

    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    run()
