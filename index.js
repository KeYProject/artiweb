const url = require("url");
const http = require('https'); // or 'https' for https:// URLs
const fs = require('fs');
const os = require('os');

const { Octokit } = require("@octokit/action");
const core = require('@actions/core');
const octokit = new Octokit();
const exec = require('@actions/exec');
const { HttpClient } = require("@actions/http-client");

// 
const TARGET = "pull-requests"
const OWNER = "keyproject"
const REPO = "key"
const ARTIFACT = "test-results"
const temp = "tmp"


/*
let localPullRequests = fs.readdirSync("pull-requests");
let activatePullRequests = [];
for (const dir of localPullRequests) {
    localPullRequests[dir] = false;
}

await octokit.request('GET /repos/{owner}/{repo}/actions/runs?branch,event,status,per_page,page,created,exclude_pull_requests,check_suite_id,head_sha}', {
owner: OWNER,
repo: REPO
})
*/

//console.log("Found following local PRs", localPullRequests)


async function updatePullRequest(pr) {
    //console.log(pr.head)
    let repo = pr.head.repo.id
    let base = pr.base.repo.id
    let branch = pr.head.ref
    for (const artifact of artifacts) {
        // console.log(repo, base, artifact.workflow_run)
        // console.log(branch, artifact.workflow_run.head_branch)
        if (artifact.workflow_run.head_branch == branch) { // may be to relaxed, may add repository information
            console.log("Found artifact", artifact.id, " for PR", pr.number)
            const target = TARGET + "/" + pr.id + '/' + artifact.id
            const filename = temp + "/" + artifact.id + ".zip"
            //await downloadArtifact(target, tmpFile, artifact.archive_download_url)
            const zipUrl = artifact.archive_download_url
            console.log("Download file", './dlzip.sh', zipUrl, filename, target)
            let error = await exec.exec('./dlzip.sh', [zipUrl, filename, target]);
            if (error != 0) {
                console.log("Error by", './dlzip.sh', [zipUrl, filename, target])
            }
        }
    }
}

const httpClient = new HttpClient("artiweb")


async function downloadArtifact(target, filename, zipUrl) {
    console.log("Download file", zipUrl)
    let error = await exec.exec('./dlzip.sh', [zipUrl, filename, target]);
    if (error != 0) {
        console.log("Error by", './dlzip.sh', [zipUrl, filename, target])
    }
    return error
    /*
    const url = new URL(zipUrl)
    const options = {
        hostname: url.host,
        path: url.pathname,
        headers: { 'User-Agent': 'Mozilla/5.0' }
    }
    console.log(options)

    await http.get(zipUrl, (response, err) => {
        console.log(err)
        response.pipe(file);
        // after download completed close filestream
        file.on("finish", () => {
            file.close();
            console.log("Download Completed");
            unpackArtifact(target, filename)
        });
    });*/
}

async function unpackArtifact(target, file) {
    mkdirSafe(target)
    console.log("Unzip ", file, " to ", target)
    exec.exec('unzip', [file, '-d', target]);
}

function mkdirSafe(f) {
    if (!fs.existsSync(f)) fs.mkdirSync(f, { recursive: true });
}

let pullRequests
let artifacts
async function main() {
    let prReq = await octokit.request('GET /repos/{owner}/{repo}/pulls', {
        owner: OWNER,
        repo: REPO
    })

    pullRequests = prReq.data
    console.log("Remote PRs", pullRequests.length)

    let aReq = await octokit.request('GET /repos/{owner}/{repo}/actions/artifacts?name={artiname}', {
        owner: OWNER,
        repo: REPO,
        artiname: ARTIFACT
    })
    artifacts = aReq.data.artifacts
    console.log("Number of artifacts:", artifacts.length)

    mkdirSafe(temp)

    for (const pr of pullRequests) { 
        console.log("Update pull request:", pr.number)
        await updatePullRequest(pr);
    }
}

main()