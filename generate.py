#!/usr/bin/python3

from collections import namedtuple
import addict
import json
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import markdown


TARGET = Path("./pull-requests")

env = Environment(loader=FileSystemLoader("templates"),
                  autoescape=select_autoescape())

def mymarkdown(txt): 
    if txt: return markdown.markdown(txt)
    else: return "" 

env.filters['markdown'] = mymarkdown

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

    total_runtimes = {arti_folder.name:  junit_statistics(arti_folder)
                      for arti_folder in pull_request.glob("*/")
                      if arti_folder.is_dir()}

    keys = sorted(list(total_runtimes.keys()))
    values = [total_runtimes[x] for x in keys]
    labels = [a.created_at
              for x in total_runtimes.keys()
              for a in artifacts
              if str(a.id) == x
              ]

    runtime_chart = {
        'type': 'bar',
        'data': {
            'labels': labels,
            'datasets': [{
                'label': 'Runtime in Hours',
                'data': [v.total_time/60.0/60.0 for v in values],
                'borderWidth': 1
            },
            ]
        },
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,
            'scales': {
                'y': {
                    'beginAtZero': True
                }
            }
        }
    }

    test_cases = {
        'type': 'line',
        'data': {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Failures',
                    'data': [v.failures for v in values],
                    'fill': True,
                    'borderColor': 'rgb(250, 192, 192)',
                    'backgroundColor': 'rgb(250, 220, 220)',
                    'tension': 0.1,
                },
                {
                    'label': 'Errors',
                    'data': [v.errors for v in values],
                    'fill': True,
                    'borderColor': 'rgb(180, 192, 192)',
                    'backgroundColor': 'rgb(200, 212, 212)',
                    'tension': 0.1,
                },
                {
                    'label': 'Skipped',
                    'data': [v.skipped for v in values],
                    'fill': True,
                    'borderColor': 'rgb(100, 100, 100)',
                    'backgroundColor': 'rgb(150, 150, 150)',
                    'tension': 0.1,
                },
                {
                    'label': 'Success',
                    'data': [v.success for v in values],
                    'fill': True,
                    'borderColor': 'rgb(75, 192, 100)',
                    'backgroundColor': 'rgb(95, 212, 120)',
                    'tension': 0.1,
                }]
        },
        'options': {
            'responsive': True,
            'maintainAspectRatio': False,

            'scales': {
                'y': {
                    'stacked': True
                }
            }
        }
    }

    # import pprint
    # pprint.pprint(test_cases)

    print(target)
    with target.open('w') as fp:
        fp.write(template.render(
            pr=data, artifacts=artifacts, runtimes=total_runtimes, rtchart=runtime_chart, tcchart=test_cases))

    data.artifacts = artifacts
    return data


def find_files(directory, pattern):
    import fnmatch
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename


JUnitStat = namedtuple(
    "JUnitStat", "total_time, total_tests, skipped, errors, failures, success")


def junit_statistics(folder: Path):
    from junitparser import JUnitXml, TestCase, TestSuite
    total_time = 0.0
    number_test_cases = 0
    skipped = 0
    error = 0
    success = 0
    failures = 0
    for f in folder.rglob("*.xml"):
        xml = JUnitXml.fromfile(f)
        total_time += xml.time

        s = xml.skipped
        t = xml.tests
        f = xml.failures
        e = xml.errors

        number_test_cases += t
        skipped += s
        error += e
        failures += f
        success += (t - f - e - s)
    return JUnitStat(total_time, number_test_cases, skipped, error, failures, success)


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
                raise e
    index()
