# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Automates the generation of release notes from version control history.

1) Finds the 2 most recent release branches and extracts the git commits
   and parses them.
2) Asks you where they are categorized as.
3) Generates an html page using a few templates.
4) Opens the browser.

You can then just copy-paste it into the email..

To run the command - inside a checked out hdctools repo:

python3 dockerfiles/release_notes_generator.py

"""

from collections import namedtuple
import datetime
import html
import re
import subprocess
import sys
import tempfile


def find_branches():
    """Finds the two most recent hdctools-release branches from git.

    It fetches all remote branches, filters for those matching the pattern
    "origin/hdctools-release-MMYY...", sorts them by year and month in
    descending order, and returns the names of the two most recent ones.

    Returns:
        tuple: A tuple containing two strings:
            (newest_branch_name, second_newest_branch_name)
    """
    args = ["git", "branch", "-r"]
    git_branch_lines = subprocess.check_output(args).decode().splitlines()
    reg = r"(cros|origin)/hdctools-release-(?P<month>\d\d)(?P<year>\d\d)\S*"
    values = [re.search(reg, x) for x in git_branch_lines]
    values = [x for x in values if x]
    values.sort(reverse=True, key=lambda x: x.group("year") + x.group("month"))
    values = [x.group() for x in values]
    return values[0], values[1]


def load_commits(commits_new_branch, commits_last_branch, cwd=None):
    """Loads git commits between two specified branches.

    It uses `git log` to retrieve the commit hash, subject (description),
    and author name for commits in the range `last_branch...new_branch`.
    Each commit's information is parsed and stored in a Commit namedtuple.

    Args:
        commits_new_branch (str): The newer branch name (or commit reference) to
            end the log at (inclusive).
        commits_last_branch (str): The older branch name (or commit reference) to
            start the log from (exclusive).
        cwd (str, optional): The current working directory to run git commands.
            Defaults to None.

    Returns:
        list: A list of Commit namedtuples, where each tuple contains
              (hash, desc, author).
    """
    delim = "␟"
    args = [
        "git",
        "log",
        f"--pretty=format:%H{delim}%s{delim}%aN",
        f"{commits_last_branch}...{commits_new_branch}",
    ]
    response = subprocess.check_output(args, cwd=cwd).decode()
    Commit = namedtuple("Commit", ["hash", "desc", "author"])
    loaded_commits = []

    for line in response.splitlines():
        loaded_commits.append(Commit(*line.split(delim)))
    return loaded_commits


def organize_help(help_headers):
    """Prints help message showing available categories for organizing commits.

    Args:
        help_headers (list): A list of strings, where each string is a category name.
    """
    print("Enter the number to organize the commit.")
    for i, name in enumerate(help_headers):
        print(f"{i}:{name}")


def handle_response(response_headers):
    """Handles user input for selecting a commit category.

    Prompts the user for input, attempts to convert it to an integer,
    and validates if it's a valid index for the provided headers list.

    Args:
        response_headers (list): A list of strings, representing available category
                        names.

    Returns:
        str or None: The selected category name (string) if the input is valid,
                     otherwise None.
    """
    response = "Invalid"
    try:
        response = input()
        index = int(response)
        if 0 <= index < len(response_headers):
            return response_headers[index]
    except (ValueError, KeyboardInterrupt):
        pass
    print(f"Invalid response: {repr(response)}")
    return None


def organize_commits(loaded_commits, commit_headers):
    """Interactively organizes a list of commits into predefined categories.

    For each commit, it prints the commit description and author, then prompts
    the user to select a category from the provided headers. This process
    repeats until all commits are categorized.

    Args:
        loaded_commits (list): A list of Commit namedtuples to be organized.
        commit_headers (list): A list of strings, where each string is a category name
                        to organize commits into.

    Returns:
        dict: A dictionary where keys are category names (from headers) and
              values are lists of Commit namedtuples belonging to that category.
    """
    organized_commits = {x: [] for x in commit_headers}
    organize_help(commit_headers)
    for loaded_commit in loaded_commits:
        while True:
            print(f"{loaded_commit.desc: <60}\t({loaded_commit.author})")
            key = handle_response(commit_headers)
            if key is not None:
                organized_commits[key].append(loaded_commit)
                break
            organize_help(commit_headers)
    return organized_commits


def format_header(name):
    """Formats a category header name into an HTML string.

    Escapes the name for HTML safety and wraps it in specific HTML
    tags with styling for display in a document.

    Args:
        name (str): The category header name.

    Returns:
        str: An HTML string representing the formatted header.
    """
    name = html.escape(name)
    template = (
        "<br>"
        '<p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;'
        '"><span style="font-size:10.5pt;font-family:Roboto,sans-serif;'
        "color:#000000;background-color:transparent;font-weight:700;"
        "font-style:normal;font-variant:normal;text-decoration:none;"
        'vertical-align:baseline;white-space:pre;white-space:pre-wrap;">'
        f"{name}"
        '</span><span style="font-size:10.5pt;font-family:Roboto,sans-serif;'
        "color:#000000;background-color:transparent;font-weight:400;"
        "font-style:normal;font-variant:normal;text-decoration:none;"
        "vertical-align:baseline;white-space:pre;white-space:pre-wrap;"
        '"><span class="Apple-tab-span" style="white-space:pre;">'
        ' </span></span><span style="font-size:10.5pt;'
        "font-family:Roboto,sans-serif;color:#000000;"
        "background-color:transparent;font-weight:400;font-style:normal;"
        "font-variant:normal;text-decoration:none;vertical-align:baseline;"
        'white-space:pre;white-space:pre-wrap;"><span class="Apple-tab-span" '
        'style="white-space:pre;"> </span></span></p>'
    )
    return template


def format_commit(commit):
    """Formats a single commit's details into an HTML string.

    Extracts the short hash, description, and author from the commit.
    It creates a clickable link to the commit on googlesource.com using
    the full hash. All parts are HTML-escaped and styled.

    Args:
        commit (namedtuple): A Commit namedtuple with 'hash', 'desc',
                             and 'author' attributes.

    Returns:
        str: An HTML string representing the formatted commit.
    """
    short_hash = html.escape(f"{commit.hash[:8]}")
    url = html.escape(f"https://chromium-review.googlesource.com/q/{commit.hash}")
    desc = html.escape(commit.desc)
    author = html.escape(f"({commit.author})")
    template = (
        '<p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;'
        '"><a href="'
        f"{url}"
        '" style="text-decoration:none;"><span style="font-size:9pt;'
        "font-family:'Roboto Mono',monospace;color:#1155cc;"
        "background-color:transparent;font-weight:400;font-style:normal;"
        "font-variant:normal;text-decoration:underline;"
        "-webkit-text-decoration-skip:none;text-decoration-skip-ink:none;"
        'vertical-align:baseline;white-space:pre;white-space:pre-wrap;">'
        f"{short_hash}"
        '</span><span style="font-size:10.5pt;font-family:Roboto,sans-serif;'
        "color:#000000;background-color:transparent;font-weight:400;"
        "font-style:normal;font-variant:normal;text-decoration:none;"
        "vertical-align:baseline;white-space:pre;white-space:pre-wrap;"
        '"><span class="Apple-tab-span" style="white-space:pre;'
        '"> </span></span></a><span style="font-size:10.5pt;'
        "font-family:Roboto,sans-serif;color:#000000;"
        "background-color:transparent;font-weight:400;font-style:normal;"
        "font-variant:normal;text-decoration:none;vertical-align:baseline;"
        'white-space:pre;white-space:pre-wrap;">'
        f"{desc}"
        '</span><span style="font-size:10.5pt;font-family:Roboto,sans-serif;'
        "color:#000000;background-color:transparent;font-weight:400;"
        "font-style:normal;font-variant:normal;text-decoration:none;"
        "vertical-align:baseline;white-space:pre;white-space:pre-wrap;"
        '"><span class="Apple-tab-span" style="white-space:pre;'
        '"> </span></span><span style="font-size:10.5pt;'
        "font-family:Roboto,sans-serif;color:#000000;"
        "background-color:transparent;font-weight:400;font-style:normal;"
        "font-variant:normal;text-decoration:none;vertical-align:baseline;"
        'white-space:pre;white-space:pre-wrap;">'
        f"{author}"
        "</span></p>"
    )
    return template


def create_temp_file(report_lines):
    """Creates a temporary HTML file, writes lines to it, and opens it.

    The file is created with a '.html' suffix and is not deleted automatically
    on close (delete=False), allowing an external program ('open') to access it.

    Args:
        report_lines (list): A list of strings, where each string is a line of HTML
                      content.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
    with tmp as f:
        f.write("\n".join(report_lines).encode())
    subprocess.call(["open", tmp.name])


def main():
    """Main function to generate release notes."""
    headers = [
        "CL List",
        "Features",
        "Bug Fixes",
        "Docs",
        "Data",
        "CI / Infrastructure",
    ]

    print("Fetching the latest remote branches...")
    subprocess.run(["git", "fetch"], check=True)

    new_branch, last_branch = find_branches()

    today = datetime.date.today()
    branch_date_match = re.search(
        r"hdctools-release-(?P<month>\d\d)(?P<year>\d\d)", new_branch
    )
    if branch_date_match:
        branch_month = int(branch_date_match.group("month"))
        branch_year = int(branch_date_match.group("year"))
        current_month = today.month
        current_year = int(today.strftime("%y"))

        if branch_month != current_month or branch_year != current_year:
            print(
                f"\nError: The newest branch '{new_branch}' does not match the "
                f"current month and year ({current_month:02d}{current_year:02d})."
            )
            print(
                "Please ensure a new release branch has been created and 'git fetch' "
                "was successful."
            )
            sys.exit(1)

    commits = load_commits(new_branch, last_branch)
    organized = organize_commits(commits, headers)

    lines = []

    for header, commits_list in organized.items():
        if commits_list:  # Only add header if there are commits in the category
            lines.append(format_header(header))
            for c in commits_list:
                lines.append(format_commit(c))

    create_temp_file(lines)
    print("\nRelease notes HTML file has been generated and opened in your browser.")


if __name__ == "__main__":
    main()
