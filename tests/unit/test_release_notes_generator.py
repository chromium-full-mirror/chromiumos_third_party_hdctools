# pylint: disable=import-error
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=unused-argument

from collections import namedtuple
import html as html_stdlib  # Alias to avoid conflict with pytest's html module

import pytest

# Assuming release_notes_generator.py is in the same directory or accessible via
# PYTHONPATH
from dockerfiles.release_notes_generator import create_temp_file
from dockerfiles.release_notes_generator import find_branches
from dockerfiles.release_notes_generator import format_commit
from dockerfiles.release_notes_generator import format_header
from dockerfiles.release_notes_generator import handle_response
from dockerfiles.release_notes_generator import load_commits
from dockerfiles.release_notes_generator import organize_commits
from dockerfiles.release_notes_generator import organize_help


# Define a Commit namedtuple similar to the one used in the script for test data
Commit = namedtuple("Commit", ["hash", "desc", "author"])


class TestFindBranches:
    def test_find_branches_success(self, mocker):
        """Tests find_branches successfully identifies and sorts branches."""
        mock_output = (
            "  origin/hdctools-release-0123-foo\n"  # year 23, month 01
            "  origin/hdctools-release-1222-bar\n"  # year 22, month 12
            "  origin/hdctools-release-0323-baz\n"  # year 23, month 03
            "  origin/other-branch\n"
        ).encode()
        mock_check_output = mocker.patch(
            "subprocess.check_output", return_value=mock_output
        )

        # Sort key is year + month, descending.
        # "23" + "03" -> "2303"
        # "23" + "01" -> "2301"
        # "22" + "12" -> "2212"
        # Expected order: origin/hdctools-release-0323-baz,
        # origin/hdctools-release-0123-foo
        expected_new_branch = "origin/hdctools-release-0323-baz"
        expected_last_branch = "origin/hdctools-release-0123-foo"

        new_branch, last_branch = find_branches()
        assert new_branch == expected_new_branch
        assert last_branch == expected_last_branch
        mock_check_output.assert_called_once_with(["git", "branch", "-r"])

    def test_find_branches_insufficient_matches(self, mocker):
        """Tests find_branches raises IndexError if less than two matches."""
        mock_output_one_match = "  origin/hdctools-release-0123-foo\n".encode()
        mocker.patch("subprocess.check_output", return_value=mock_output_one_match)
        with pytest.raises(IndexError):
            find_branches()

        mock_output_no_match = "  origin/other-branch\n".encode()
        mocker.patch("subprocess.check_output", return_value=mock_output_no_match)
        with pytest.raises(IndexError):
            find_branches()

    class TestLoadCommits:
        DELIM = "␟"

        def test_load_commits_success(self, mocker):
            """Tests load_commits parses git log output correctly."""
            mock_output = (
                f"hash1{self.DELIM}Desc 1{self.DELIM}Author One\n"
                f"hash2{self.DELIM}Desc 2{self.DELIM}Author Two\n"
            ).encode()
            mock_subprocess = mocker.patch(
                "subprocess.check_output", return_value=mock_output
            )

            commits_list = load_commits("new_branch", "last_branch", cwd=".")

            assert len(commits_list) == 2
            assert commits_list[0] == Commit(
                hash="hash1", desc="Desc 1", author="Author One"
            )
            assert commits_list[1] == Commit(
                hash="hash2", desc="Desc 2", author="Author Two"
            )

            expected_args = [
                "git",
                "log",
                f"--pretty=format:%H{self.DELIM}%s{self.DELIM}%aN",
                "last_branch...new_branch",
            ]
            mock_subprocess.assert_called_once_with(expected_args, cwd=".")

        def test_load_commits_no_output(self, mocker):
            """Tests load_commits returns an empty list for no git log output."""
            mocker.patch("subprocess.check_output", return_value=b"")
            commits_list = load_commits("new", "old")
            assert not commits_list

    def test_organize_help_prints_correctly(self, capsys):
        """Tests organize_help prints the expected help message."""
        headers = ["Features", "Bug Fixes"]
        organize_help(headers)
        captured = capsys.readouterr()
        expected_output = (
            "Enter the number to organize the commit.\n0:Features\n1:Bug Fixes\n"
        )
        assert captured.out == expected_output

    class TestHandleResponse:
        HEADERS = ["Features", "Bug Fixes", "Docs"]

        def test_valid_input(self, mocker):
            mocker.patch("builtins.input", return_value="1")
            response = handle_response(self.HEADERS)
            assert response == "Bug Fixes"

        def test_invalid_index_too_high(self, mocker, capsys):
            mocker.patch("builtins.input", return_value="5")
            response = handle_response(self.HEADERS)
            assert response is None
            assert "Invalid response: '5'" in capsys.readouterr().out

        def test_invalid_index_negative(self, mocker, capsys):
            mocker.patch("builtins.input", return_value="-1")
            response = handle_response(self.HEADERS)
            assert response is None
            assert "Invalid response: '-1'" in capsys.readouterr().out

        def test_non_numeric_input(self, mocker, capsys):
            mocker.patch("builtins.input", return_value="abc")
            response = handle_response(self.HEADERS)
            assert response is None
            assert "Invalid response: 'abc'" in capsys.readouterr().out

        def test_keyboard_interrupt(self, mocker, capsys):
            mocker.patch("builtins.input", side_effect=KeyboardInterrupt)
            response = handle_response(self.HEADERS)
            assert response is None
            assert "Invalid response: Invalid" not in capsys.readouterr().out

    class TestOrganizeCommits:
        HEADERS = ["Features", "Fixes", "Chores"]
        COMMITS_DATA = [
            Commit(hash="h1", desc="Feature A", author="User1"),
            Commit(hash="h2", desc="Fix B", author="User2"),
            Commit(hash="h3", desc="Chore C", author="User1"),
        ]

        def test_basic_flow(self, mocker, capsys):
            mock_org_help = mocker.patch(
                "dockerfiles.release_notes_generator.organize_help"
            )
            # Simulate user inputs: "Features", then "Fixes", then "Chores"
            mock_handle_resp = mocker.patch(
                "dockerfiles.release_notes_generator.handle_response",
                side_effect=["Features", "Fixes", "Chores"],
            )

            organized = organize_commits(self.COMMITS_DATA, self.HEADERS)

            assert mock_org_help.call_count >= 1  # Called at least at the start
            mock_org_help.assert_any_call(self.HEADERS)

            assert mock_handle_resp.call_count == 3
            for unused_header in self.HEADERS:
                mock_handle_resp.assert_any_call(self.HEADERS)

            captured = capsys.readouterr().out
            assert f"{'Feature A': <60}\t(User1)" in captured
            assert f"{'Fix B': <60}\t(User2)" in captured
            assert f"{'Chore C': <60}\t(User1)" in captured

            assert len(organized["Features"]) == 1
            assert organized["Features"][0].desc == "Feature A"
            assert len(organized["Fixes"]) == 1
            assert organized["Fixes"][0].desc == "Fix B"
            assert len(organized["Chores"]) == 1
            assert organized["Chores"][0].desc == "Chore C"

        def test_invalid_input_retry(self, mocker, capsys):
            mock_org_help = mocker.patch(
                "dockerfiles.release_notes_generator.organize_help"
            )
            # Simulate: invalid input, then valid "Features"
            mock_handle_resp = mocker.patch(
                "dockerfiles.release_notes_generator.handle_response",
                side_effect=[None, "Features"],
            )
            single_commit = [self.COMMITS_DATA[0]]

            organized = organize_commits(single_commit, self.HEADERS)

            # organize_help called at start, then again after invalid input
            assert mock_org_help.call_count == 2
            assert mock_handle_resp.call_count == 2

            assert len(organized["Features"]) == 1
            assert organized["Features"][0].desc == "Feature A"

    def test_format_header_output(self):
        """Tests the HTML output of format_header."""
        name = "New Features & Updates"
        escaped_name = html_stdlib.escape(name)
        # This is brittle, but necessary if the exact HTML is required.
        expected_html = (
            "<br>"
            '<p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;'
            '"><span style="font-size:10.5pt;font-family:Roboto,sans-serif;'
            "color:#000000;background-color:transparent;font-weight:700;"
            "font-style:normal;font-variant:normal;text-decoration:none;"
            'vertical-align:baseline;white-space:pre;white-space:pre-wrap;">'
            f"{escaped_name}"
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
        assert format_header(name) == expected_html


def test_format_commit_output():
    """Tests the HTML output of format_commit."""
    commit = Commit(
        hash="abcdef123456",
        desc="Implement cool feature & stuff",
        author="Dev Person <dev@example.com>",
    )

    short_hash = html_stdlib.escape(commit.hash[:8])
    url = html_stdlib.escape(
        f"https://chromium-review.googlesource.com/q/{commit.hash}"
    )
    desc = html_stdlib.escape(commit.desc)
    author_text = html_stdlib.escape(f"({commit.author})")

    expected_html = (
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
        f"{author_text}"
        "</span></p>"
    )
    assert format_commit(commit) == expected_html


def test_create_temp_file_functionality(mocker):
    """Tests create_temp_file writes to a temp file and calls 'open'."""
    mock_named_temp_file = mocker.patch("tempfile.NamedTemporaryFile")
    mock_subprocess_call = mocker.patch("subprocess.call")

    # Mock the file object returned by NamedTemporaryFile
    mock_file_obj = mocker.MagicMock()
    mock_file_context_manager = mocker.MagicMock()
    mock_file_context_manager.__enter__.return_value = mock_file_obj
    mock_file_context_manager.name = "placeholder_temp_file.html"
    mock_named_temp_file.return_value = mock_file_context_manager

    report_lines = ["<h1>Title</h1>", "<p>Content</p>"]
    create_temp_file(report_lines)

    mock_named_temp_file.assert_called_once_with(suffix=".html", delete=False)
    mock_file_obj.write.assert_called_once_with(
        "<h1>Title</h1>\n<p>Content</p>".encode()
    )
    mock_subprocess_call.assert_called_once_with(["open", "placeholder_temp_file.html"])

    # Note: The main execution block of release_notes_generator.py is not unit tested
    # here, as it involves direct calls to these functions in sequence.
    # Testing each function individually provides good coverage.
    # An integration test could be written for the main block if desired.# In
    # release_notes_generator.py
