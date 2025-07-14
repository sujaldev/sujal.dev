from src.build import load_config, make_jinja_env, build_home

from flask import Flask

app = Flask(__name__)
env = make_jinja_env(live=True)


@app.route("/")
def home():
    env.globals.update(load_config())
    return build_home(env, minified=False, live=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
