---
name: test-docker-orchestrator
description: "Use this skill to autonomously build, push, and execute servod hardware tests via the Test Orchestrator using Docker. This coordinates building local code, running the orchestrator service on the Cloudtop, instructing the user to connect their local host agent, and executing the test payload. Use whenever the user asks to test servod on local hardware, run Docker hardware tests, or use the Test Orchestrator."
---

# test-docker-orchestrator

This skill guides you through seamlessly executing `servod` hardware-in-the-loop (HIL) tests. This pathway runs `servod` inside Docker containers on a local physical machine (laptop/gLinux) that communicates with a Cloudtop orchestrator via an SSH tunnel on port 5002.

**CRITICAL RULE:** Follow these steps in order. Do not skip the Orchestrator setup.

## 1. Gather Required Information
If the user requests a local docker test, gather missing information via `ask_user` if not provided:
1. **Commands to Run:** What `dut-control` commands they want to execute (e.g., `servo_fw_version ec_board`)
2. **DUT Information:** A list of `board,model,serial` for all connected devices.

## 2. Build and Push Local Code
Build and push the new Docker image containing the user's modifications:
```bash
cd src/third_party/hdctools/development_environment
./build_and_push.sh
cd ../../../../
```
*Note the image name pushed (usually `us-docker.pkg.dev/chromeos-hw-tools-dev/servod-scratch/servod:<username>`). If this build fails due to unresolvable compilation issues (like protobuf mismatches), inform the user and fallback to the stable `us-docker.pkg.dev/chromeos-hw-tools-dev/servod/servod:release` image for the test to ensure the Orchestrator pipeline still runs.*

## 3. Start the Orchestrator on Cloudtop
Ensure the orchestrator is running on **Port 5002** (the expected tunnel port). You must build its image first:
```bash
cd src/third_party/hdctools/tests/hardware/orchestrator
docker build -t test_orchestrator .
docker rm -f orchestrator || true
docker run -d --name orchestrator -p 5002:5000 test_orchestrator
cd ../../../../
```

## 4. Setup Local Host (User Handoff)
The local agent must run on the physical machine connected to the hardware. **Provide this exact block to the user and PAUSE:**

> I have prepared the Orchestrator on your Cloudtop. Please run this exact command on your **local physical machine** to connect the agent:
> 
> ```bash
> scp <YOUR_CLOUDTOP_HOSTNAME>:/<ABSOLUTE_PATH_TO_HDCTOOLS>/tests/hardware/orchestrator/bootstrap_agent.sh .
> chmod +x bootstrap_agent.sh
> pkill -f "ssh -fN -L 5002:localhost:5002" || true
> ./bootstrap_agent.sh <YOUR_CLOUDTOP_HOSTNAME> /<ABSOLUTE_PATH_TO_HDCTOOLS>
> ```
> 
> **Please reply with "Ready" when your terminal prints `Polling http://localhost:5002 every 10 seconds`.**

*(Use `ask_user` or wait for the user's reply in chat before proceeding to step 5).*

## 5. Execute the Test Suite
Create `local_duts.csv` containing the `board,model,serial` matrix requested by the user.

Then, execute the robust python runner:
```bash
./src/third_party/hdctools/tests/hardware/orchestrator/run_test_plan.py local_duts.csv --image <IMAGE_NAME> --cmds <CMD1> <CMD2>
```

## 6. Generate Report
Once `run_test_plan.py` completes, copy its output into a clear, formatted Markdown summary for the user. Highlight which physical serials passed and which failed.
