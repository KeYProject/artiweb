#!/usr/bin/python3

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

GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

PRIVATE_TOKEN = os.environ['PRIVATE_TOKEN']


def updatePullRequest(pr):
    repo = pr.head.repo.id
    branch = pr.head.ref

    folder = TARGET / pr.number
    with (folder / "meta.json").open('w') as fp:
        json.dump(pr, fp)

    for artifact in artifacts:
        arti_head = artifact.workflow_run.head_repository_id
        if arti_head == repo and artifact.workflow_run.head_branch == branch:
            print("Found artifact", artifact.id, " for PR", pr.number)
            target = folder / artifact.id
            filename = temp / (artifact.id + ".zip")
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

        mkdirSafe(targetFolder)
        import zipfile
        with zipfile.ZipFile(targetFile, 'r') as zip_ref:
            zip_ref.extractall(targetFolder)
        targetFile.unlink()


def mkdirSafe(f):
    try:
        os.mkdir(f)
    except:
        pass


pullRequests = []
artifacts = []


def get_json(path, **args):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{path}".format(**args)
    import helper 
    return helper.ObjDict(requests.get(url).json())


def main():
    prReq = get_json('pulls')
    pullRequests = prReq.data
    print("Remote PRs", pullRequests.length)
    aReq = get_json("actions/artifacts?name={artiname}", artiname=ARTIFACT)
    artifacts = aReq.data.artifacts
    print("Number of artifacts:", artifacts.length)

    mkdirSafe("meta")

    with open("meta/pull-requests.json", "w") as fp:
        json.dump(pullRequests, fp)
    with open("meta/artifacts.json") as fp:
        json.dump(artifacts, fp)

    mkdirSafe(temp)

    for pr in pullRequests:
        print("Update pull request:", pr.number)
        updatePullRequest(pr)

main()
