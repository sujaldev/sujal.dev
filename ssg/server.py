import functools

from ssg.build import *
from ssg.constants import *

from flask import Flask

MINIFIED = False

app = Flask(__name__)
env = make_jinja_env(live=True)


def live_config(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        env.globals.update(load_config())
        return func(*args, **kwargs)

    return wrapper


@app.route("/")
@live_config
def home():
    return build_home(env, minified=MINIFIED, live=True)


@app.route("/blog")
@live_config
def blog():
    return build_blog(env, minified=MINIFIED, live=True)


def run(host="0.0.0.0", port=5000, minify=False):
    global MINIFIED
    MINIFIED = minify

    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    run()
