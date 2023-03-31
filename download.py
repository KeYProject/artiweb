#!/usr/bin/python3

from time import sleep
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

with open("meta/artifacts.json") as fp:
    OLD_META =  json.load(fp)

def updatePullRequest(pr, artifacts):
    repo = pr.head.repo.id
    branch = pr.head.ref

    folder = TARGET / str(pr.number)
    folder.mkdir(exist_ok=True, parents=True)
    with (folder / "meta.json").open('w') as fp:
        json.dump(pr, fp)

    pr_artifacts = []

    for artifact in artifacts:
        arti_head = artifact.workflow_run.head_repository_id
        if arti_head == repo and artifact.workflow_run.head_branch == branch:
            pr_artifacts.append(artifact.id)
            target = folder / str(artifact.id)
            filename = temp / (str(artifact.id) + ".zip")
            zipUrl = artifact.archive_download_url
            
            old_filesize = get_old_downloaded_file_size(artifact.id)
            new_filesize = artifact.size_in_bytes
            downloadArtifact(target, filename, zipUrl, new_filesize != old_filesize)

            with (target / 'meta.json').open('w') as fp:
                json.dump(artifact, fp)
    print("Artifacts for", pr.number, "found:", pr_artifacts)


def get_old_downloaded_file_size(id : int) -> int:    
    for a in OLD_META: 
        if a.id == id:
            return a.size_in_bytes
    return -1



def downloadArtifact(targetFolder: Path, tmpFile: Path, zipUrl : str, file_size_changed : bool):
    """Download and unpack the given zipUrl at the targetFolder. tmpFile is used as intermediate storage. 
    Download and unpack only if it is necessary."""

    if not targetFolder.exists() or file_size_changed:
        if not tmpFile.exists() or file_size_changed:
            mkdirSafe(tmpFile.parent)
            with tmpFile.open('wb') as f:
                r = requests.get(zipUrl, headers={"Authorization": f"token {PRIVATE_TOKEN}"}, timeout=60)
                r.raise_for_status()
                f.write(r.content)
        try:
            mkdirSafe(targetFolder)
            with zipfile.ZipFile(tmpFile, 'r') as zip_ref:
                zip_ref.extractall(targetFolder)
            tmpFile.unlink()
        except zipfile.BadZipFile as e: 
            print("Failed to open zip file:", e, tmpFile)


def mkdirSafe(f):
    try:
        os.mkdir(f)
    except:
        pass


def get_json(path, args):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{path}"
    print("Fetching", url, "with args", args)
    r = requests.get(url, args)
    r.raise_for_status()
    j = r.json()
    if isinstance(j, list):
        return list(map(Dict, j))
    else:
        return Dict(j)


def get_json_all(path, args, extract=lambda x: x):
    args['page'] = 1
    args['per_page'] = 100
    results = []
    while True:
        page = get_json(path, args)

        sleep(250) # try to avoid hitting rate limits

        e = extract(page)
        if e:
            results += e
        else:
            return results
        args['page'] += 1


def main():
    pullRequests = get_json_all('pulls', {"state": "all"})
    print("Found", len(pullRequests), "pull requests")

    artifacts = get_json_all("actions/artifacts", {"name": str(ARTIFACT)}, lambda p: p["artifacts"])
    print(f"Number of artifacts: {len(artifacts)}")

    mkdirSafe("meta")

    with open("meta/pull-requests.json", "w") as fp:
        json.dump(pullRequests, fp)
    with open("meta/artifacts.json", 'w') as fp:
        json.dump(artifacts, fp)

    mkdirSafe(temp)
        
    for pr in pullRequests:
        print("Updating pull request:", pr.number)
        updatePullRequest(pr, artifacts)

main()
