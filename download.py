#!/usr/bin/python3

from time import sleep
import zipfile
from addict import Dict
import requests
import json
from pathlib import Path
import os
import logging
import shutil


TARGET = Path("pull-requests")
OWNER = Path("keyproject")
REPO = Path("key")
ARTIFACT = Path("test-results")
temp = Path("tmp")

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

PRIVATE_TOKEN = os.environ.get('PRIVATE_TOKEN', '')

OLD_ARTIFACTS_BY_ID = {}

class Data:
    def __init__(self, artifacts, old_artifacts):
        self.artifacts = artifacts
        self.old_artifacts_by_id = { a["id"]: Dict(a) for a in old_artifacts }

    def find_artifacts(self, repo, branch):
        return [a for a in self.artifacts 
                if a.workflow_run.head_repository_id == repo and
                    a.workflow_run.head_branch == branch]
    
    def find_old_artifact(self, id):
        return self.old_artifacts_by_id.get(id)
    
    def update_old_artifact(self, id, to):
        self.old_artifacts_by_id.update({id: to})

def update_pull_request(pr, data: Data):
    repo = pr.head.repo.id
    branch = pr.head.ref

    folder = TARGET / str(pr.number)
    folder.mkdir(exist_ok=True, parents=True)
    with (folder / "meta.json").open('w') as fp:
        json.dump(pr, fp)

    pr_artifacts = []

    for artifact in data.find_artifacts(repo, branch):
        pr_artifacts.append(artifact.id)
        target = folder / str(artifact.id)
        filename = temp / (str(artifact.id) + ".zip")
        zip_url = artifact.archive_download_url

        old_artifact = data.find_old_artifact(artifact.id)
        if old_artifact is None: 
            force_update = True
            logging.info(f"Downloading artifact {artifact.id}, no earlier version found")
        else:
            old_filesize = old_artifact.size_in_bytes
            new_filesize = artifact.size_in_bytes
            force_update = new_filesize != old_filesize

            if force_update:
                logging.info(f"Re-downloading artifact {artifact.id} because it was changed: {new_filesize} != {old_filesize}")
        
        download_artifact(target, filename, zip_url, force_update)

        with (target / 'meta.json').open('w') as fp:
            json.dump(artifact, fp)

        data.update_old_artifact(artifact.id, artifact)
    
    logging.info(f"Artifacts for {pr.number} found: {pr_artifacts}")

def download_artifact(target_folder: Path, tmp_file: Path, zip_url: str, force_update: bool) -> bool:
    """Download and unpack the given zipUrl at the targetFolder. tmpFile is used as intermediate storage. 
    Download and unpack only if it is necessary."""

    if not target_folder.exists() or force_update:
        if not tmp_file.exists() or force_update:
            logging.debug(f"Downloading {zip_url}")
            mkdir_safe(tmp_file.parent)
            with tmp_file.open('wb') as f:
                r = requests.get(zip_url, headers={
                                 "Authorization": f"token {PRIVATE_TOKEN}"}, timeout=60)
                r.raise_for_status()
                f.write(r.content)
        try:
            shutil.rmtree(target_folder)
            logging.debug(f"Extracting {tmp_file} to {target_folder}")
            mkdir_safe(target_folder)
            with zipfile.ZipFile(tmp_file, 'r') as zip_ref:
                zip_ref.extractall(target_folder)
            tmp_file.unlink()
            return True
        except zipfile.BadZipFile as e:
            logging.error(f"Failed to open zip file {tmp_file}: {e}")
            return False


def mkdir_safe(f):
    try:
        os.mkdir(f)
    except:
        pass


def get_json(path, args):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{path}"
    logging.debug(f"Fetching {url} with args {args}")
    r = requests.get(url, args, timeout=60)
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

        sleep(0.250)  # try to avoid hitting rate limits

        e = extract(page)
        if e:
            results += e
        else:
            return results
        args['page'] += 1


def initLogging():
    logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s', level=logging.DEBUG)

def main():
    initLogging()

    old_artifacts = []
    downloaded_artifacts_path = Path("meta/downloads.json")
    if downloaded_artifacts_path.is_file():
        try:
            with downloaded_artifacts_path.open() as fp:
                old_artifacts = json.load(fp)
        except json.decoder.JSONDecodeError as e:
            logging.warn("Failed to read old downloads, removing file")
            os.remove(downloaded_artifacts_path)
    else:
        logging.info("Old downloads file not found, full redownload")

    logging.info("Start downloading process")

    pull_requests = get_json_all('pulls', {"state": "all"})
    pull_requests.sort(key = lambda x: x.number)
    logging.info(f"Found {len(pull_requests)} pull requests")

    artifacts = get_json_all(
        "actions/artifacts", {"name": str(ARTIFACT)}, lambda p: p["artifacts"])
    logging.info(f"Number of artifacts: {len(artifacts)}")

    mkdir_safe("meta")

    with open("meta/pull-requests.json", "w") as fp:
        json.dump(pull_requests, fp)

    with open("meta/artifacts.json", 'w') as fp:
        json.dump(artifacts, fp)

    mkdir_safe(temp)

    data = Data(artifacts, old_artifacts)
    for pr in pull_requests:
        logging.info(f"Updating pull request {pr.number}")
        update_pull_request(pr, data)
        with downloaded_artifacts_path.open("w") as fp:
            json.dump(list(data.old_artifacts_by_id.values()), fp)

if __name__ == '__main__':
    main()
