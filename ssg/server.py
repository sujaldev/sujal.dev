import functools
import inspect
from mimetypes import types_map as mimetype_map

import ssg.build as build
import ssg.constants as consts

import frontmatter
import minify
from quart import Quart, Response, websocket
from watchfiles import awatch

with open(consts.SRC_DIR / "reload.js") as file:
    RELOAD_SCRIPT = "<script>" + \
                    minify.string(mimetype_map['.js'], file.read()) + \
                    "</script>"


def inject_js_reloader(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        html: str = await func(*args, **kwargs)
        if isinstance(html, str):
            html += RELOAD_SCRIPT
        return html

    return wrapper


def route(*args, **kwargs):
    def decorator(func):
        func._route_args = args
        func._route_kwargs = kwargs
        return func

    return decorator


def ws(*args, **kwargs):
    def decorator(func):
        func._websocket_args = args
        func._websocket_kwargs = kwargs
        return func

    return decorator


class Server:
    def __init__(self, host="0.0.0.0", port=5000, minified=False, include_drafts=False):
        self.host = host
        self.port = port
        self.minified = False
        self.include_drafts = include_drafts

        self.app = Quart(__name__)

        self.builder = build.Builder(
            minified=minified,
            live=True,
            include_drafts=include_drafts,
        )

        self.register_views()

    def register_views(self):
        [
            self.app.route(
                *getattr(method, "_route_args"),
                **getattr(method, "_route_kwargs")
            )(method)
            for attr in dir(self)
            if inspect.ismethod(method := getattr(self, attr))
            if "_route_args" in dir(method)
        ]

        [
            self.app.websocket(
                *getattr(method, "_websocket_args"),
                **getattr(method, "_websocket_kwargs")
            )(method)
            for attr in dir(self)
            if inspect.ismethod(method := getattr(self, attr))
            if "_websocket_args" in dir(method)
        ]

    async def reload_on_changes(self):
        async for changes in awatch(consts.CONTENT_DIR, consts.SRC_DIR):
            for change_type, file_path in changes:
                if file_path == str(consts.CONTENT_DIR / "config.toml"):
                    self.builder.load_config()

            await websocket.send("reload")

    @inject_js_reloader
    @route("/")
    async def home(self):
        return self.builder.build_home(self.builder.load_posts(5))

    @inject_js_reloader
    @route("/blog")
    async def blog(self):
        return self.builder.build_blog_index(self.builder.load_posts())

    @inject_js_reloader
    @route("/post/<slug>")
    async def blog_post(self, slug):
        # This assumes unique slugs but that is not enforced yet, (unlikely) problem for future me.
        file_path = tuple((consts.CONTENT_DIR / "posts/").rglob(f"*-{slug}.md"))[0]
        with open(file_path) as post:
            post = frontmatter.load(post).to_dict()

        if post.get("draft", False) and not self.include_drafts:
            return Response(
                "<h1>This post is currently a draft, enable <code>include_drafts</code> to see this post.</h1>",
                status=404
            )

        post["slug"] = post.get("slug", slug)

        return self.builder.build_blog_post(post)

    @route("/ws")
    async def ws_healthcheck(self):
        return Response(status=200)

    @ws("/ws")
    async def ws(self):
        await websocket.accept()
        await self.reload_on_changes()

    def run(self):
        self.app.run(self.host, self.port, debug=True)


if __name__ == "__main__":
    Server().run()
