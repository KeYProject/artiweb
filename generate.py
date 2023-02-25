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

def index(pull_requests):
    template = env.get_template("index.html")
    target = TARGET / "index.html"
    target.parent.mkdir(exist_ok=True)
    pull_requests.sort(key=lambda x: x.number)

    tests = {}
    for pr in pull_requests:
        for a in pr.artifacts:
            for t in a.tests:
                t.created_at_pretty = a.created_at_pretty
                t.created_at = a.created_at
                if t.full_name in tests:
                    tests[t.full_name].append(t)
                else:
                    tests[t.full_name] = [t]
    
    graphs = []
    for name, ts in tests.items():
        ts.sort(key=lambda t: t.created_at)
        labels = [t.created_at_pretty for t in ts]
        values = [t.statistics.total_time/60.0/60.0 for t in ts]

        graph = generate_runtime_chart(labels, values)
        graphs.append({ "graph": graph, "name": name })

    graphs.sort(key=lambda x: x["name"])
    
    with target.open('w', encoding="utf-8") as fp:
        fp.write(template.render(pullrequests=pull_requests, graphs=graphs))


def read_meta(folder: Path):
    with (folder/"meta.json").open("r", encoding="utf-8") as fp:
        return addict.Dict(json.load(fp))


def generate_runtime_chart(labels, data):
    return {
        'type': 'bar',
        'data': {
            'labels': labels,
            'datasets': [{
                'label': 'Runtime in Hours',
                'data': data,
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

def generate_pull_request(path: Path):
    template = env.get_template("pr.html")
    print("Reading meta")
    pr = read_meta(path)

    path.mkdir(exist_ok=True)

    print("Generating artifacts")
    artifacts = [generate_artifact(arti_folder)
                 for arti_folder in path.glob("*/")
                 if arti_folder.is_dir()]
    
    print("Rendering artifacts")
    for artifact in artifacts:
        render_artifact(artifact, pr)

    print("Rendered", len(artifacts), "artifacts") 

    artifacts.sort(key=lambda x: x.created_at)

    values = [a.statistics for a in artifacts]
    labels = [a.created_at_pretty for a in artifacts]

    print("Generating charts")
    runtime_chart = generate_runtime_chart(labels, [v.total_time/60.0/60.0 for v in values])

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
            test.full_name = project + ":" + name

            html_file_path = html_files_path / name / "index.html"
            if html_file_path.is_file():
                test.report_path = html_file_path.parent.relative_to(path)
            
            tests.append(test)
    return tests

def generate_artifact(path: Path):
    artifact = read_meta(path)
    artifact.path = path
    artifact.id = path.name
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
        fp.write(template.render(pr=pr, artifact=artifact))

if __name__ == '__main__':
    path: Path
    pull_requests = []
    for path in TARGET.glob("*/"):
        if path.is_dir():
            print("Generating pull request", path.relative_to(TARGET))
            try:
                pr = generate_pull_request(path)
                pull_requests.append(pr)
            except Exception as e:
                print("Error generating", path, e)
    index(pull_requests)
