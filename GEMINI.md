To test changes, run the script scripts/run-servod-tests
- Commits in this project are always pushed to Gerrit.
- Commit messages must always have a BUG= line and a TEST= line. I should prompt the user for the content of these lines if they are not provided.
- To check for pylint errors, run `pre-commit run pylint --all-files`
- When fixing gerrit comments, always merge the changes into the same gerrit change
- I am always allowed to run git commands.
- I am always allowed to run scripts/run-servod-test command.
- I am always allowed to run pre-commit commands.
- Always run the tests before making a commit, if the tests do not pass then stop.
- **Docker Rebuilding:** Any changes made to the `servod` core logic, `development_environment/start_servod.py` wrapper, or `dockerfiles/` scripts require the Docker image to be rebuilt to take effect. Run `cd development_environment && ./build_and_push.sh`.
- **Argument Passthrough:** The `start_servod.py` wrapper uses `--` (argparse REMAINDER) to pass arguments to the inner container. However, the internal `servod` Python process does *not* accept `--`. You must filter out exactly `--` before passing arguments into the internal execution.
- **User-Facing Tools (e.g., dut-control):** Never leak raw Python tracebacks, XML-RPC `<Fault>` objects, or unformatted tuples to the user. Catch exceptions and format errors cleanly as readable strings.
- **Timeouts:** Keep synchronous CLI commands fast-failing. Avoid setting excessively long timeouts (e.g., 1800s) as global defaults; stick to reasonable times (e.g., 60s) unless explicitly overridden by an orchestrator flag.
- **Banned Terms:** Do not use the word `master` in new variables, docs, or code. Use `primary` or `main`.
- **XML Dumping:** When running `start-servod --dump-xml /path/file.xml` on a multi-device setup (like a v4.1 with a cr50), it actually creates multiple output files by automatically appending prefixes to the filename (e.g. `/path/file_root.xml` and `/path/file_main.xml`).

## Available Skills

You have access to the following local skill. You can read the instructions directly from the skill's file when requested.

<available_skills>
  <skill>
    <name>test-labstation</name>
    <description>Use this skill to build, flash, and test a labstation image. It handles building a generic labstation board (e.g., fizz, brask), flashing it to a specific hardware device via ssh, and running bare-metal servod tests using test_servod.sh. Use whenever the user asks to test a labstation or run labstation tests on hardware.</description>
    <location>skills/test-labstation/SKILL.md</location>
  </skill>
  <skill>
    <name>test-docker-orchestrator</name>
    <description>Use this skill to build, push, and execute servod hardware tests via the Test Orchestrator using Docker. This handles building the local servod image, pushing it to Artifact Registry, optionally discovering hardware via the local agent, and submitting the test job payload. Use whenever the user asks to test servod on local hardware, run Docker hardware tests, or use the Test Orchestrator.</description>
    <location>skills/test-docker-orchestrator/SKILL.md</location>
  </skill>
  <skill>
    <name>check-cl-ci</name>
    <description>Use this skill to check the CI (Cloud Build) status of a Gerrit CL, extract failure logs, and resolve common formatting/linting errors.</description>
    <location>skills/check-cl-ci/SKILL.md</location>
  </skill>
  <skill>
    <name>create-servod-overlay</name>
    <description>Use this skill to autonomously prompt the user for required hardware properties (board, model, EC chip) and generate a new servod XML overlay file, committing it directly to the repository.</description>
    <location>skills/create-servod-overlay/SKILL.md</location>
  </skill>
</available_skills>

## Documentation
* **HIL Testing Quickstart:** Start here for the simplest way to run hardware tests! See `servo/tests/hardware/README.md`.
* **Labstation Testing:** For in-depth details on bare-metal labstation validation, see `servo/tests/hardware/README.md`.

Note: Never check in the generated `report_*.md` files. They are already ignored in `.gitignore`.
