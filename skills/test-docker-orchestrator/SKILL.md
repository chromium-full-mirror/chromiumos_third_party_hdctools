---
name: test-docker-orchestrator
description: "Use this skill to build, push, and execute servod hardware tests via the Test Orchestrator using Docker. This handles building the local servod image, pushing it to Artifact Registry, optionally discovering hardware via the local agent, and submitting the test job payload. Use whenever the user asks to test servod on local hardware, run Docker hardware tests, or use the Test Orchestrator."
---

# test-docker-orchestrator

This skill guides you through executing `servod` hardware-in-the-loop (HIL) tests using the Test Orchestrator. This pathway runs `servod` inside Docker containers on a local physical machine (gLinux/laptop) that communicates with the Cloudtop orchestrator via an SSH tunnel.

## Required Information (CRITICAL)
If the user requests a local docker test but does not provide the necessary parameters, you **MUST ask the user** for the missing information before proceeding. 

Gather the following:
1. **Target Image Name:** (Usually `us-docker.pkg.dev/chromeos-hw-tools-dev/servod-scratch/servod:haddowk`)
2. **Commands to Run:** What `dut-control` commands they want to execute (e.g., `servo_fw_version ec_board`)
3. **DUT Information:** A CSV list (or array) of `board,model,serial` for all connected devices.

**Discovery Tip:** If the user does not know the serial numbers connected to their local machine, you can automatically discover them:
```bash
./src/third_party/hdctools/servo/tests/hardware/discover.py --backend local --out discovered_duts.csv
```

## Execution Steps

### 1. Verify Orchestrator & Agent
The Orchestrator must be running in Docker on the Cloudtop, and the `local_agent` must be running on the user's physical machine.

Check if Orchestrator is running:
```bash
docker ps | grep orchestrator
```
*(If not running, you must start it: `docker run -d --name orchestrator -p 5000:5000 test_orchestrator gunicorn --bind 0.0.0.0:5000 app:app`)*

### 2. Build and Push Image (If Code Changed)
If the user modified Python code in `hdctools`, you MUST build and push the new Docker image before testing:
```bash
cd src/third_party/hdctools/development_environment
./build_and_push.sh
cd ../../../../
```

### 3. Create the DUT Matrix
Create a `local_duts.csv` file containing the `board,model,serial` list.

### 4. Execute the Test Suite
Run the orchestrator wrapper script. It will read the CSV and submit parallel API jobs to `localhost:5000`.

```bash
./run_multidut_orchestrator.sh local_duts.csv
```
*(If the user wants different commands, you may need to temporarily edit the `CMDS=` variable inside `run_multidut_orchestrator.sh` before running).*

### 5. Generate Report
Once the execution finishes, read the output from the generated `orchestrator_report_*.txt` files. 

Synthesize the exit codes and any stderr logs into a clear Markdown summary for the user, highlighting which physical serials passed and which failed (e.g. due to hardware cable issues).
