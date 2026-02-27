# Servod Remote Testing Setup

This document describes how to set up and use the remote testing framework for `servod`. This allows developers to build and manage tests from a Cloudtop environment while the actual `servod` instance runs and interacts with hardware on a local gLinux machine (like a laptop or Bruschetta).

## Architecture Overview

1.  **Cloudtop:** Hosts the development environment, code, build process, and a Test Orchestrator service.
2.  **Local gLinux:** Connects to the physical hardware. Runs a Local Agent that communicates with the Cloudtop's Test Orchestrator via an SSH tunnel.
3.  **SSH Tunnels:**
    *   **Control Tunnel:** Local machine tunnels a port to the Cloudtop, allowing the Local Agent to poll the Test Orchestrator.
    *   **Servod API Tunnel (Optional):** Local machine tunnels the `servod` API port to the Cloudtop for direct access.

## Setup Instructions

**1. On Cloudtop:**

   a.  **Clone Repository:** Ensure you have the `hdctools` repository cloned.

   b.  **Configure Docker for Artifact Registry:**
       ```bash
       gcloud auth login
       gcloud auth configure-docker us-docker.pkg.dev
       ```

   c.  **Build and Run Test Orchestrator Docker Image:**
       ```bash
       cd hdctools/development_environment/test_orchestrator
       # Build the image
       docker build -t test_orchestrator .
       # Run the container in detached mode
       docker run -d --name orchestrator --restart always -p 5000:5000 test_orchestrator gunicorn --bind 0.0.0.0:5000 --timeout 120 app:app
       ```
       To see logs: `docker logs -f orchestrator`
       To stop: `docker stop orchestrator && docker rm orchestrator`

**2. On Local gLinux Machine:**

   a.  **Install Docker:** Follow the standard Docker installation instructions for gLinux.

   b.  **Configure Docker for Artifact Registry:**
       ```bash
       gcloud auth login
       gcloud auth configure-docker us-docker.pkg.dev
       ```

   c.  **Install `start-servod` / `stop-servod`:** Ensure these scripts (from `hdctools`) are available and in your `PATH`.

   d.  **Copy `local_agent.py`:** Copy `hdctools/development_environment/local_agent.py` from your Cloudtop to a suitable location on your local machine (e.g., `~/local_agent.py`). Make it executable:
       ```bash
       chmod +x ~/local_agent.py
       ```

   e.  **Install Python Dependencies for Agent:**
       ```bash
       sudo apt update
       sudo apt install python3-pip
       pip3 install requests
       ```

   f.  **Run SSH Tunnels:** Replace `<CLOUDTOP_HOSTNAME>` with your Cloudtop's hostname (e.g., `yourname.c.googlers.com`).

       *   **Control Tunnel (Required):**
           ```bash
           ssh -fN -L 5002:localhost:5000 <CLOUDTOP_HOSTNAME>
           ```
           Keep this tunnel running.

       *   **Servod API Tunnel (Optional):**
           ```bash
           ssh -R 9998:localhost:9999 <CLOUDTOP_HOSTNAME>
           ```
           Keep this tunnel running if you need direct `servod` API access from the Cloudtop.

   g.  **Run Local Agent:** In a new terminal on the local machine:
       ```bash
       ~/local_agent.py
       ```
       This agent will now poll the Cloudtop orchestrator for jobs.

## Development Workflow

1.  **Modify Code:** Make changes to the `servod` code within the `hdctools` directory on your Cloudtop.

2.  **Build and Push Image:** Run the build script on your Cloudtop:
    ```bash
    cd /path/to/hdctools/development_environment
    ./build_and_push.sh
    ```
    This updates the `us-docker.pkg.dev/chromeos-hw-tools-dev/servod-scratch/servod:haddowk` image.

3.  **Trigger Test:** On your Cloudtop, send a request to the Test Orchestrator to start a test run. You can specify the commands to run using the `test_commands` array.

    ```bash
    IMAGE="us-docker.pkg.dev/chromeos-hw-tools-dev/servod-scratch/servod:haddowk"
    # Example: Run servo_fw_version
    curl -X POST -H "Content-Type: application/json" \
         -d "{ \"image_name\": \"$IMAGE\", \"test_commands\": [\"servo_fw_version\"] }" \
         http://localhost:5000/api/jobs

    # Example: Run multiple commands
    curl -X POST -H "Content-Type: application/json" \
         -d "{ \"image_name\": \"$IMAGE\", \"test_commands\": [\"servo_fw_version\", \"cpu_temp\"] }" \
         http://localhost:5000/api/jobs
    ```
    Note the `job_id` returned in the JSON response.

4.  **Monitor:** The Local Agent on your gLinux machine will detect the job, pull the new image, run the test, and send results back.

5.  **Get Results:** Once the test is complete, retrieve the results on your Cloudtop using the `job_id`:
    ```bash
    curl http://localhost:5000/api/results/<job_id> | jq '.'
    ```
    The JSON output will contain:
    *   `test_outputs`: A dictionary where keys are the commands and values are their results (stdout, stderr, exit_code).
    *   `log`: The contents of the `latest.DEBUG` log from `servod`.
    *   `exit_code`: 0 if all test commands passed, non-zero otherwise.
    *   `error`: Any general error messages.

## Troubleshooting

*   **Connection Refused:** Ensure the SSH tunnels are running and that the Test Orchestrator service is active on the Cloudtop.
*   **Authentication Errors:** Double-check that `gcloud auth configure-docker` has been run on both machines.
*   **`start-servod` not found:** Ensure the `hdctools` scripts directory is in your `PATH` on the local machine.
*   **Logs:** Check the terminal output of the Test Orchestrator on the Cloudtop (`docker logs -f orchestrator`) and the Local Agent on the local machine for errors.

## Using with Gemini

Once the setup is complete and the services/tunnels are running, you can instruct Gemini to use this system. Here are some example prompts:

*   "I've made changes to `some_file.py`. Please build the servod image and run the remote hardware test for `servo_fw_version`."
*   "Build and push the image, then trigger the remote test to check `servo_fw_version` and `dut_lab_config`."

Gemini should then:

1.  Execute `./hdctools/development_environment/build_and_push.sh`.
2.  Send the API request to `http://localhost:5000/api/jobs` with the appropriate `test_commands` array to start the test.
3.  Retrieve the results using the returned `job_id` from `http://localhost:5000/api/results/<job_id>`.
4.  Report the test outcome and logs back to you.
