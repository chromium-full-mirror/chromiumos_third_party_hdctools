# Local Machine Setup for Test Orchestra

To allow an agent or orchestrator to run tests on your local hardware (e.g., Brya Banshee), follow these setup instructions.

## 1. Hardware Connection
1.  Connect your **Servo device** (e.g., Servo V4.1) to your host machine via the **HOST** USB port.
2.  Connect the **Servo** to the **DUT** (e.g., Brya Banshee) via the appropriate cable (e.g., USB-C Suzy-Q or Servo Micro).
3.  Ensure the DUT is powered.

## 2. Software Requirements
Ensure your host machine has the following installed:
- **Docker**: Used to run servod containers.
- **Python 3.8+**: Used to run the local agent.
- **Git**: To clone the repository.

## 3. Permissions
The user running the local agent must have permissions to access USB devices and run Docker.
```bash
sudo usermod -aG docker $USER
sudo usermod -aG plugdev $USER
```
*(You may need to logout and login for group changes to take effect.)*

## 4. Network Configuration (Cloudtop to Local)
The **Test Orchestra** works by having a central Orchestrator (on Cloudtop) and a Local Agent (on your machine).

### Option A: Orchestrator on Cloudtop, Agent on Local Machine
1.  **On Cloudtop:** Start the orchestrator service.
    ```bash
    python3 development_environment/test_orchestrator/app.py --port 5000
    ```
2.  **On Local Machine:** Set up an SSH tunnel to forward your local port 5002 to Cloudtop's port 5000.
    ```bash
    ssh -R 5000:localhost:5000 your_cloudtop_instance
    ```
    *Alternatively, if you want the agent to reach Cloudtop:*
    ```bash
    ssh -L 5002:localhost:5000 your_cloudtop_instance
    ```
3.  **On Local Machine:** Start the agent pointing to the tunnel.
    ```bash
    python3 development_environment/local_agent.py --orchestrator_url http://localhost:5002
    ```

## 5. Running the Local Agent
1.  Navigate to the `hdctools` directory.
2.  Install dependencies:
    ```bash
    pip install -r development_environment/requirements_test.txt
    ```
3.  Start the local agent:
    ```bash
    python3 development_environment/local_agent.py --orchestrator_url http://localhost:5002
    ```

## 6. Verification
Once the agent is running, it will poll the orchestrator for jobs. You should see logs indicating polling activity.

```text
Local agent started. Polling http://localhost:5002 every 10 seconds.
```

## 7. Troubleshooting
- **No devices found:** Run `lsusb` to ensure the Servo and GSC (Cr50/Ti50) are detected.
- **Docker permission denied:** Ensure your user is in the `docker` group.
- **Connection refused:** Ensure the SSH tunnel is active and the orchestrator is running.
