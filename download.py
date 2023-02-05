#!/usr/bin/python3

import zipfile
from addict import Dict
import requests
import json
from pathlib import Path
import subprocess
import os
import sys


TARGET = Path("pull-requests")
OWNER = Path("keyproject")
REPO = Path("key")
ARTIFACT = Path("test-results")
temp = Path("tmp")

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

PRIVATE_TOKEN = os.environ.get('PRIVATE_TOKEN', '')


def updatePullRequest(pr):
    repo = pr.head.repo.id
    branch = pr.head.ref

    folder = TARGET / str(pr.number)
    folder.mkdir(exist_ok=True, parents=True)
    with (folder / "meta.json").open('w') as fp:
        json.dump(pr, fp)

    for artifact in artifacts:
        arti_head = artifact.workflow_run.head_repository_id
        print(arti_head, repo,  artifact.workflow_run.head_branch, branch)
        if arti_head == repo and artifact.workflow_run.head_branch == branch:
            print("Found artifact", artifact.id, " for PR", pr.number)
            target = folder / str(artifact.id)
            filename = temp / (str(artifact.id) + ".zip")
            zipUrl = artifact.archive_download_url
            downloadArtifact(target, filename, zipUrl)

            with (target / 'meta.json').open('w') as fp:
                json.dump(artifact, fp)


def downloadArtifact(targetFolder: Path, targetFile: Path, zipUrl):
    if not targetFolder.exists():
        if not targetFile.exists():
            mkdirSafe(targetFile.parent)
            with targetFile.open('wb') as f:
                r = requests.get(zipUrl, headers={
                                 "Authorization": f"token {PRIVATE_TOKEN}"})
                f.write(r.content)
        try:
            mkdirSafe(targetFolder)
            with zipfile.ZipFile(targetFile, 'r') as zip_ref:
                zip_ref.extractall(targetFolder)
            targetFile.unlink()
        except zipfile.BadZipFile as e: 
            print(e, targetFile)


def mkdirSafe(f):
    try:
        os.mkdir(f)
    except:
        pass


pullRequests = []
artifacts = []


def get_json(path, **args):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{path}".format(**args)
    print(url)
    j = requests.get(url).json()
    if isinstance(j, list):
        return list(map(Dict, j))
    else:
        return Dict(j)


def get_json_all(url, per_page=100, results_key='artifacts', **kwargs):
    sfx = "&per_page={per_page}&page={page}"
    kwargs['page'] = 0
    kwargs['per_page'] = per_page
    results = []
    while True:
        kwargs['page'] += 1
        page = get_json(url + sfx, **kwargs)
        if page[results_key]:
            results += page[results_key]
        else:
            return results


def main():
    global pullRequests, artifacts
    pullRequests = get_json('pulls')
    print(f"Remote PullRequests {len(pullRequests)}")
    artifacts = get_json_all(
        "actions/artifacts?name={artiname}", artiname=ARTIFACT)
    print(f"Number of artifacts: {len(artifacts)}")

    mkdirSafe("meta")

    with open("meta/pull-requests.json", "w") as fp:
        json.dump(pullRequests, fp)
    with open("meta/artifacts.json", 'w') as fp:
        json.dump(artifacts, fp)

    mkdirSafe(temp)

    for pr in pullRequests:
        print("Update pull request:", pr.number)
        updatePullRequest(pr)


main()
