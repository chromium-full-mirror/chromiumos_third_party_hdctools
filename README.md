#  HDCTools (Hardware Debug Control Tools)

Welcome to the `hdctools` repository. This project contains the software stack for interacting with ChromeOS hardware debug targets, most notably the **Servo** family of debug boards (Servo v2, Servo v4, Servo Micro, C2D2, SuzyQable, etc.).

The core component of this repository is `servod`, a daemon that abstracts the complex hardware interfaces (I2C, UART, SPI, GPIO) of the Servo ecosystem into a unified control plane.

## 🚀 The "Fission" Architecture

`hdctools` is transitioning to the **Fission** architecture. This represents a major modernization effort for the repository, including:
*   **gRPC Interface:** Shifting from legacy XML-RPC to a robust, high-performance gRPC API for `servod` communication.
*   **Containerization:** `servod` and its dependencies are now heavily Dockerized for reproducible development, testing, and deployment.
*   **Test Orchestration:** A new `local_agent` and Docker Orchestrator workflow for scalable Hardware-in-the-Loop (HIL) and labstation testing.

## 📚 Documentation

*   **[Hardware Testing Quickstart](tests/hardware/README.md):** Start here if you are a test operator or developer looking to run tests against physical hardware locally or on a remote labstation.
*   **[Design & Core Docs](docs/):** Detailed documentation on `servod`, `ec-3po`, power measurement, and specific Servo hardware revisions.

## 🛠️ Development & Testing

This project requires strict adherence to code quality and testing standards.

### Running Tests
Always run the test suite before submitting a CL. The testing framework leverages Docker for consistency:
```bash
./scripts/run-servod-tests
```

### Linting
Check for pylint errors using `pre-commit`:
```bash
pre-commit run pylint --all-files
```

## 🤝 Contributing

Commits in this project are pushed to ChromeOS Gerrit. Ensure your commit messages follow the standard formatting and **always** include a `BUG=` and `TEST=` line.

```text
component: concise description of changes

Longer explanation of why these changes were made, what bugs they fix,
and how the new architecture handles the problem.

BUG=b:12345678
TEST=scripts/run-servod-tests and manual validation steps
```
