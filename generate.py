#!/usr/bin/python3

from collections import namedtuple
import addict
import json
import os
import re
from datetime import datetime

from functools import reduce

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import markdown


TARGET = Path("./pull-requests")

env = Environment(loader=FileSystemLoader("templates", encoding="utf-8"),
                  autoescape=select_autoescape())

def mymarkdown(txt): 
    if txt: return markdown.markdown(txt)
    else: return "" 

env.filters['markdown'] = mymarkdown

PULL_REQUESTS = []


def index():
    template = env.get_template("index.html")
    target = TARGET / "index.html"
    target.parent.mkdir(exist_ok=True)
    requests = sorted(PULL_REQUESTS, key=lambda x: x.number)

    with target.open('w', encoding="utf-8") as fp:
        fp.write(template.render(pullrequests=requests))


def read_meta(folder: Path):
    with (folder/"meta.json").open("r", encoding="utf-8") as fp:
        return addict.Dict(json.load(fp))


def generate_pull_request(path: Path):
    template = env.get_template("pr.html")
    print("Reading meta")
    pr = read_meta(path)
    PULL_REQUESTS.append(pr)

    path.mkdir(exist_ok=True)

    print("Generating artifacts")
    artifacts = [generate_artifact(arti_folder)
                 for arti_folder in path.glob("*/")
                 if arti_folder.is_dir()]
    
    print("Rendering artifacts")
    for artifact in artifacts:
        render_artifact(artifact, pr)

    print("Rendered", len(artifacts), "artifacts") 
    artifacts = sorted(artifacts, key=lambda x: x.created_at)

    values = [a.statistics for a in artifacts]
    labels = [a.created_at_pretty for a in artifacts]

    print("Generating charts")
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

    print("Rendering index.html")
    target = path / "index.html"
    with target.open('w', encoding="utf-8") as fp:
        fp.write(template.render(
            pr=pr, artifacts=artifacts, rtchart=runtime_chart, tcchart=test_cases))

    pr.artifacts = artifacts
    return pr

JUnitStat = namedtuple(
    "JUnitStat", "total_time, total_tests, skipped, errors, failures, success")

def combine_stats(a, b):
    total_time = a.total_time + b.total_time
    total_tests = a.total_tests + b.total_tests
    skipped = a.skipped + b.skipped
    errors = a.errors + b.errors
    failures = a.failures + b.failures
    success = a.success + b.success
    return JUnitStat(total_time, total_tests, skipped, errors, failures, success)

def junit_statistics(folder: Path):
    from junitparser import JUnitXml
    acc = JUnitStat(0, 0, 0, 0, 0, 0)
    for f in folder.rglob("*.xml"):
        try:
            xml = JUnitXml.fromfile(f)
            s = xml.skipped
            t = xml.tests
            f = xml.failures
            e = xml.errors
            stat = JUnitStat(
                xml.time,
                t,
                s,
                e,
                f,
                (t - f - e - s)
            )
            acc = combine_stats(acc, stat)
        except Exception as e:
            print("Skipping malformed file", f, e)
    return acc

def find_tests(path: Path):
    projects = [p for p in path.glob("*/") if p.is_dir()]
    tests = []
    for project_path in projects:
        build_path = project_path / "build"
        project_tests = [p for p in (build_path / "test-results") .glob("*/") if p.is_dir()]
        project = project_path.name
        html_files_path = build_path / "reports" / "tests"
        for test_path in project_tests:
            name = test_path.name

            test = addict.Dict()
            test.statistics = junit_statistics(test_path)
            test.project = project
            test.name = name

            html_file_path = html_files_path / name / "index.html"
            if html_file_path.is_file():
                test.report_path = html_file_path
            
            tests.append(test)
    return tests

def generate_artifact(path: Path):
    artifact = read_meta(path)
    artifact.path = path
    t = datetime.strptime(artifact.created_at, "%Y-%m-%dT%H:%M:%SZ")
    artifact.created_at_pretty = t.strftime("%d. %b %Y %H:%M")
    
    tests = find_tests(path)
    
    artifact.tests = tests
    artifact.statistics = reduce(lambda acc, value: combine_stats(acc, value.statistics), tests, JUnitStat(0, 0, 0, 0, 0, 0))
    return artifact

def render_artifact(artifact, pr):
    template = env.get_template("artifact.html")
    artifact.path.mkdir(exist_ok=True)
    target = artifact.path / "index.html"
    with target.open('w', encoding="utf-8") as fp:
        tests = artifact.tests
        fp.write(
            template.render(pr=pr, artifact=artifact, tests=tests))

if __name__ == '__main__':
    pr: Path
    for pr in TARGET.glob("*/"):
        if pr.is_dir():
            print("Generating pull request", pr.relative_to(TARGET))
            try:
                generate_pull_request(pr)
            except Exception as e:
                print("Error generating", pr, e)
                #raise e
    index()
