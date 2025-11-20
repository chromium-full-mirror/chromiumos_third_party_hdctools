To test changes, run the script scripts/run-servod-tests
- Commits in this project are always pushed to Gerrit.
- Commit messages must always have a BUG= line and a TEST= line. I should prompt the user for the content of these lines if they are not provided.
- To check for pylint errors, run `pre-commit run pylint --all-files`
- When fixing gerrit comments, always merge the changes into the same gerrit change
- I am always allowed to run git commands.
- I am always allowed to run scripts/run-servod-test command.
- I am always allowed to run pre-commit commands.
- Always run the tests before making a commit, if the tests do not pass then stop.
