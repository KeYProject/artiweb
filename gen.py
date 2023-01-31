#!/usr/bin/python3

import json, os

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

PUBLIC = Path("./public")

env = Environment(loader=FileSystemLoader("templates"),
                  autoescape=select_autoescape())


def index():
    template = env.get_template("index.html")
    target = PUBLIC / "index.html"
    target.parent.mkdir(exist_ok=True)

    with target.open('w') as fp:
        fp.write(template.render(pullrequests=PULL_REQUESTS))


def render_pull_request(pull_request):
    template = env.get_template("pr.html")
    target = PUBLIC / str(pull_request['number']) / "index.html"
    target.parent.mkdir(exist_ok=True)

    with target.open('w') as fp:
        fp.write(template.render(pr=pull_request))

    for artifact in pull_request['artifacts']:
        render_artifact(pull_request, artifact)


def render_artifact(pull_request, artifact):
    template = env.get_template("artifact.html")
    target = PUBLIC / str(pull_request['number']) / str(
        artifact['id']) / "index.html"

    # find all index.html
    from glob import glob
    indexes = glob(str(target.parent) + "/**/index.html")

    target.parent.mkdir(exist_ok=True)

    with target.open('w') as fp:
        fp.write(
            template.render(pr=pull_request,
                            artifact=artifact,
                            indexes=indexes))


with open('meta/pull-requests.json') as fp:
    PULL_REQUESTS = json.load(fp)

with open('meta/artifacts.json') as fp:
    ARTIFACTS = json.load(fp)

import shutil

if __name__ == '__main__':
    try:
        shutil.copytree("pull-requests", "public")
    except:
        pass

    for p in PULL_REQUESTS:
        branch = p['head']['ref']
        p['artifacts'] = [
            a for a in ARTIFACTS if a['workflow_run']['head_branch'] == branch
        ]

    index()

    for pull_request in PULL_REQUESTS:
        render_pull_request(pull_request)
