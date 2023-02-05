#!/usr/bin/python3

from benedict import benedict
import json
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

TARGET = Path("./pull-requests")

env = Environment(loader=FileSystemLoader("templates"),
                  autoescape=select_autoescape())

PULL_REQUESTS = []
ARTIFACTS = []


def index():
    global PUBLIC
    template = env.get_template("index.html")
    target = PUBLIC / "index.html"
    target.parent.mkdir(exist_ok=True)

    with target.open('w') as fp:
        fp.write(template.render(pullrequests=PULL_REQUESTS))


def read_meta(folder: Path):
    return benedict(folder/"meta.json", format='json')


def render_pull_request(pull_request: Path):
    template = env.get_template("pr.html")
    data = read_meta(pull_request)
    PULL_REQUESTS.append(data)

    target = pull_request / "index.html"
    target.parent.mkdir(exist_ok=True)

    artifacts = [generate_artifact(pull_request, arti_folder)
                 for arti_folder in pull_request]

    with target.open('w') as fp:
        fp.write(template.render(pr=data, artifacts=artifacts))

    data.artifacts = artifacts
    return data


def find_files(directory, pattern):
    import fnmatch
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename


def generate_artifact(pull_request: benedict, artifact: Path):
    template = env.get_template("artifact.html")
    target = artifact / "index.md"
    data = read_meta(artifact)
    ARTIFACTS.append(data)

    # find all index.html
    prefix = len(str(target.parent))
    #indexes = [x[prefix+1:] for x in find_files(target.parent, "index.html")]
    indexes = list(artifact.rglob("index.html"))
    if "index.html" in indexes:
        indexes.remove("index.html")

    target.parent.mkdir(exist_ok=True)

    with target.open('w') as fp:
        fp.write(
            template.render(pr=pull_request, artifact=data, indexes=indexes))

if __name__ == '__main__':
    for pr in TARGET:
        generate_pull_request(pr)
    index()
