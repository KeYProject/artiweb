#!/usr/bin/python3

import addict
import json
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import markdown


TARGET = Path("./pull-requests")

env = Environment(loader=FileSystemLoader("templates"),
                  autoescape=select_autoescape())

env.filters['markdown'] = markdown.markdown

PULL_REQUESTS = []
ARTIFACTS = []


def index():
    template = env.get_template("index.html")
    target = TARGET / "index.html"
    target.parent.mkdir(exist_ok=True)

    with target.open('w') as fp:
        fp.write(template.render(pullrequests=PULL_REQUESTS))


def read_meta(folder: Path):
    with (folder/"meta.json").open() as fp:
        return addict.Dict(json.load(fp))


def generate_pull_request(pull_request: Path):
    template = env.get_template("pr.html")
    data = read_meta(pull_request)
    PULL_REQUESTS.append(data)

    target = pull_request / "index.html"
    target.parent.mkdir(exist_ok=True)

    artifacts = [generate_artifact(pull_request, arti_folder)
                 for arti_folder in pull_request.glob("*/")
                 if arti_folder.is_dir()]

    total_runtimes = {arti_folder.name:  total_runtime(arti_folder)
                      for arti_folder in pull_request.glob("*/")
                      if arti_folder.is_dir()}

    keys = sorted(list(total_runtimes.keys()))

    runtime_chart = {'type': 'bar',
                     'data': {
                         'labels': keys,
                             'datasets': [{
                                 'label': 'runtime',
                                 'data': [total_runtimes[k][0] for k in keys],
                                 'borderWidth': 1
                             },
                             {
                                 'label': 'test cases',
                                 'data': [total_runtimes[k][1] for k in keys],
                                 'borderWidth': 1
                             },
                             ]
                     },
                     'options': {
                         'scales': {
                             'y': {
                                 'beginAtZero': True
                             }
                         }
                     }
                     }



    with target.open('w') as fp:
        fp.write(template.render(
            pr=data, artifacts=artifacts, runtimes=total_runtimes, rtchart=runtime_chart))

    data.artifacts = artifacts
    return data


def find_files(directory, pattern):
    import fnmatch
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename


def total_runtime(folder: Path):
    from junitparser import JUnitXml, TestCase, TestSuite
    total_time = 0.0
    number_test_cases = 0
    print(list(folder.rglob("*")))

    for f in folder.rglob("*.xml"):
        xml = JUnitXml.fromfile(f)
        for suite in xml:
            case: TestCase
            for case in suite:
                total_time += case.time
                number_test_cases += 1
    return total_time, number_test_cases


def generate_artifact(pull_request, artifact: Path):
    template = env.get_template("artifact.html")
    target = artifact / "index.html"
    data = read_meta(artifact)
    ARTIFACTS.append(data)

    # find all index.html
    prefix = len(str(target.parent))
    # indexes = [x[prefix+1:] for x in find_files(target.parent, "index.html")]
    indexes = list(artifact.rglob("index.html"))
    if "index.html" in indexes:
        indexes.remove("index.html")

    target.parent.mkdir(exist_ok=True)

    with target.open('w') as fp:
        fp.write(
            template.render(pr=pull_request, artifact=data, indexes=indexes))
    return data


if __name__ == '__main__':
    pr: Path
    for pr in TARGET.glob("*/"):
        if pr.is_dir():
            try:
                generate_pull_request(pr)
            except Exception as e:
                print(e)
    index()
