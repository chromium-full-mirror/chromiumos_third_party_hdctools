---
name: check-cl-ci
description: "Use this skill to check the CI (Cloud Build) status of a Gerrit CL, extract failure logs, and resolve common formatting/linting errors."
---

# check-cl-ci

This skill guides you through checking the continuous integration (CI) status for ChromeOS `hdctools` CLs, reading the Cloud Build logs if the CI fails, and fixing common pre-commit issues.

## 1. Check CI Status on Gerrit
Gerrit's REST API prepends `)]}'` to its JSON responses to prevent XSS. You **MUST** strip this out using `tail -n +2` before parsing with `jq`.

```bash
curl -s "https://chromium-review.googlesource.com/changes/chromiumos%2Fthird_party%2Fhdctools~<CHANGE_NUMBER>/messages" | tail -n +2 | jq -r '.[-5:] | .[] | .author.name + ": " + .message'
```
*Look for the most recent message from `488603086791@cloudbuild.gserviceaccount.com`.*
* If it says `Code-Review+1` and `SUCCESS`, the CI passed!
* If it says `Code-Review-1` and `FAILURE`, copy the **Evaluation ID** (e.g., `c8edca95-...`).

## 2. Fetch the Cloud Build Logs
The Gerrit comment provides a Cloud Build link with `project=488603086791`. **Do not use the project number.** `gcloud` requires the Project ID, which is `chromeos-hw-tools-dev`.

```bash
gcloud builds log <EVALUATION_ID> --project=chromeos-hw-tools-dev
```
*Read the output to determine which build step failed.*

## 3. Fixing Common Failures
Most CI failures in this repository are caused by the strict `pre-commit` hooks. If the logs indicate a failure in `isort`, `black`, or `pylint`, you can automatically fix them locally.

```bash
# To run all hooks on the changed files:
gpkg pre-commit run --files <file1> <file2>

# Or to run a specific hook to auto-format:
gpkg pre-commit run black --files <file1>
gpkg pre-commit run isort --files <file1>
```
*Note: `gpkg pre-commit` runs inside a docker container. Do NOT run standard `pre-commit` directly.*

After fixing the files, amend your commit (`git commit --amend --no-edit`) and push the new patch set to Gerrit.
