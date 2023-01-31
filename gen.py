#!/usr/bin/python3

import json

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

PUBLIC = Path("./public")

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape()
)

def index():
    template = env.get_template("index.html")
    target = PUBLIC / "index.html"
    with target.open('w') as fp:
        fp.write(template.render())


def render_pull_request(pull_request):
    template = env.get_template("index.html")
    target = PUBLIC / "index.html"
    with target.open('w') as fp:
        fp.write(template.render())
    


if __name__ == '__main__':
    index()


