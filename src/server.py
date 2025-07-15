from src.build import load_config, make_jinja_env, build_home

from flask import Flask

MINIFIED = False

app = Flask(__name__)
env = make_jinja_env(live=True)


@app.route("/")
def home():
    env.globals.update(load_config())
    return build_home(env, minified=MINIFIED, live=True)


def run(host="0.0.0.0", port=5000, minify=False):
    global MINIFIED
    MINIFIED = minify

    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    run()
