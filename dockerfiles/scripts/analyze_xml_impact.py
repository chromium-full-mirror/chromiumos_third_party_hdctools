#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Analyzes the impact of changes to servo XML data files."""

import argparse
from collections import defaultdict
import difflib
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


# Path to the preprocessing tool
PREPROCESS_TOOL = os.path.join(os.path.dirname(__file__), "preprocess_xml.py")


def build_dependency_graph(data_dir):
    """Builds a graph where graph[included_file] = [list of files that include it]."""
    graph = defaultdict(set)
    for root_dir, unused_dirs, files in os.walk(data_dir):
        for filename in files:
            if not filename.endswith(".xml"):
                continue
            path = os.path.join(root_dir, filename)
            rel_path = os.path.relpath(path, data_dir)
            try:
                tree = ET.parse(path)
                root_elem = tree.getroot()
                for include_name in root_elem.findall(".//include/name"):
                    if include_name.text:
                        included_file = include_name.text.strip()
                        # Graph stores keys as relative paths from data_dir
                        graph[included_file].add(rel_path)
            except ET.ParseError:
                continue
    return graph


def get_affected_files(changed_files, graph, data_dir):
    """Recursively finds all files affected by the changes."""
    affected = set()
    # changed_files are paths from repo root. Convert to relative from data_dir.
    to_process = [
        os.path.relpath(f, data_dir) for f in changed_files if f.endswith(".xml")
    ]
    processed = set()

    while to_process:
        current = to_process.pop()
        if current in processed:
            continue
        processed.add(current)

        if current in graph:
            for including_file in graph[current]:
                if including_file not in affected:
                    affected.add(including_file)
                    to_process.append(including_file)

    return affected


def run_preprocess(input_file, output_file):
    """Runs the preprocess_xml.py tool."""
    try:
        subprocess.run(
            [sys.executable, PREPROCESS_TOOL, input_file, output_file],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Preprocessor failed: {e.stderr.strip()}") from e


def get_diff(file1, file2):
    """Returns the diff between two files."""
    result = subprocess.run(
        ["diff", "-u", file1, file2], capture_output=True, text=True, check=False
    )
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description="Analyze impact of XML changes.")
    parser.add_argument("--data-dir", default="servo/data", help="Path to servo/data")
    parser.add_argument("--changed-files", nargs="+", help="List of changed files")
    parser.add_argument(
        "--base-commit", default="HEAD~1", help="Base commit to compare against"
    )
    parser.add_argument(
        "--target-commit", default="HEAD", help="Target commit to compare"
    )
    parser.add_argument("--output-report", help="Path to save the report")
    parser.add_argument("--output-diff", help="Path to save the main diff")
    parser.add_argument("--html-diff-dir", help="Directory to save HTML diffs")
    parser.add_argument("--diff-url-prefix", help="Base URL prefix for diff links")
    parser.add_argument("--full-html-report", help="Path to save the full HTML report")
    args = parser.parse_args()

    if not args.changed_files:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", args.base_commit, args.target_commit],
                capture_output=True,
                text=True,
                check=True,
            )
            args.changed_files = result.stdout.splitlines()
        except Exception as e:
            print(f"Error getting changed files from git: {e}", file=sys.stderr)
            # If base_commit is missing, try to find a base commit in main
            try:
                print("Attempting to find base commit in main...", file=sys.stderr)
                subprocess.run(["git", "fetch", "origin", "main"], check=False)
                result = subprocess.run(
                    ["git", "merge-base", "origin/main", args.target_commit],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                base = result.stdout.strip()
                result = subprocess.run(
                    ["git", "diff", "--name-only", base, args.target_commit],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                args.changed_files = result.stdout.splitlines()
                args.base_commit = base
            except Exception as e2:
                print(f"Failed to find base commit: {e2}", file=sys.stderr)
                sys.exit(1)

    data_dir_rel = args.data_dir
    changed_in_data = [
        f
        for f in args.changed_files
        if f.startswith(data_dir_rel) and f.endswith(".xml")
    ]

    if not changed_in_data:
        print("No XML files in data directory changed.")
        return

    graph = build_dependency_graph(data_dir_rel)
    affected = get_affected_files(changed_in_data, graph, data_dir_rel)

    all_to_report = affected | {
        os.path.relpath(f, data_dir_rel) for f in changed_in_data
    }
    top_level = sorted(
        [
            f
            for f in all_to_report
            if os.path.basename(f).startswith("servo_") and f.endswith("_overlay.xml")
        ]
    )

    if not top_level:
        top_level = sorted(list(all_to_report))

    # Setup before and after environments
    before_base = tempfile.mkdtemp()
    after_base = tempfile.mkdtemp()

    def extract_to(commit, target_dir):
        print(f"Extracting {commit} to {target_dir}...", file=sys.stderr)
        tar_proc = subprocess.Popen(
            ["git", "archive", "--format=tar", commit, data_dir_rel],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        tar_extract = subprocess.Popen(
            ["tar", "-x", "-C", target_dir],
            stdin=tar_proc.stdout,
            stderr=subprocess.PIPE,
        )

        tar_proc.stdout.close()
        archive_stderr = tar_proc.stderr.read().decode("utf-8")
        extract_stderr_bytes = tar_extract.communicate()[1]
        extract_stderr = (
            extract_stderr_bytes.decode("utf-8") if extract_stderr_bytes else ""
        )

        if tar_proc.wait() != 0:
            raise RuntimeError(f"git archive failed for {commit}: {archive_stderr}")
        if tar_extract.wait() != 0:
            # tar_extract.communicate() already waited,
            # but we check wait() for good measure
            raise RuntimeError(f"tar extraction failed: {extract_stderr}")

        return os.path.join(target_dir, data_dir_rel)

    try:
        before_dir = extract_to(args.base_commit, before_base)
        after_dir = extract_to(args.target_commit, after_base)
    except Exception as e:
        print(f"Error extracting files from git: {e}", file=sys.stderr)
        sys.exit(1)

    report = []
    report.append("### Servo XML Impact Analysis")
    report.append(
        f"Modified files: {', '.join([os.path.basename(f) for f in changed_in_data])}"
    )
    report.append("")

    temp_out_dir = tempfile.mkdtemp()
    main_diff_path = (
        args.output_diff
        if args.output_diff
        else os.path.join(temp_out_dir, "main.diff")
    )

    functional_changes = []
    other_changes = []
    func_data = []
    other_data = []

    for f in top_level:
        display_name = f.replace("servo_", "").replace("_overlay.xml", "")
        before_path = os.path.join(before_dir, f)
        after_path = os.path.join(after_dir, f)

        processed_before = os.path.join(temp_out_dir, f.replace("/", "_") + ".before")
        processed_after = os.path.join(temp_out_dir, f.replace("/", "_") + ".after")

        has_before = os.path.exists(before_path)
        has_after = os.path.exists(after_path)

        status = "Mod"
        if not has_before:
            status = "New"
        elif not has_after:
            status = "Del"

        diff_summary_md = ""
        diff_summary_html = ""
        if has_before and has_after:
            try:
                run_preprocess(before_path, processed_before)
                run_preprocess(after_path, processed_after)

                with open(processed_before, "r", encoding="utf-8") as fb, open(
                    processed_after, "r", encoding="utf-8"
                ) as fa:
                    before_lines = fb.readlines()
                    after_lines = fa.readlines()

                diff = get_diff(processed_before, processed_after)
                if not diff:
                    status = "NoChange"
                else:
                    # Count only actual changed lines, ignoring context and headers
                    changed_lines = [
                        line
                        for line in diff.splitlines()
                        if (line.startswith("+") or line.startswith("-"))
                        and not (line.startswith("+++") or line.startswith("---"))
                    ]
                    line_count = len(changed_lines)
                    diff_summary_md = f"{line_count} lines changed"
                    diff_summary_html = diff_summary_md

                    if args.html_diff_dir and args.diff_url_prefix:
                        html_diff = difflib.HtmlDiff().make_file(
                            before_lines,
                            after_lines,
                            f"{f} (Before)",
                            f"{f} (After)",
                            context=True,
                            numlines=5,
                        )
                        html_filename = f.replace("/", "_") + ".html"
                        os.makedirs(args.html_diff_dir, exist_ok=True)
                        html_path = os.path.join(args.html_diff_dir, html_filename)
                        with open(html_path, "w", encoding="utf-8") as hf:
                            hf.write(html_diff)

                        diff_url = f"{args.diff_url_prefix}/{html_filename}"
                        diff_summary_md = f"[{line_count} lines changed]({diff_url})"
                        diff_summary_html = (
                            f'<a href="{diff_url}">{line_count} lines changed</a>'
                        )

                    with open(main_diff_path, "a", encoding="utf-8") as main_f:
                        main_f.write(f"--- {f} (PROCESSED)\n")
                        main_f.write(f"+++ {f} (PROCESSED)\n")
                        main_f.write(diff)
                        main_f.write("\n\n")
            except Exception as e:
                diff_summary_md = f"Err: {e}"
                diff_summary_html = diff_summary_md

        if status == "NoChange":
            other_changes.append(f"| {display_name} | {status} | |")
            other_data.append((display_name, status))
        else:
            functional_changes.append(
                f"| {display_name} | {status} | {diff_summary_md} |"
            )
            func_data.append((display_name, status, diff_summary_html))

    report = []
    if args.full_html_report and args.diff_url_prefix:
        full_report_url = (
            f"{args.diff_url_prefix}/{os.path.basename(args.full_html_report)}"
        )
        report.append(f"**[View Full HTML Report]({full_report_url})**")
        report.append("")

    report.append(
        f"This change affects **{len(functional_changes)}** "
        "configurations functionally."
    )
    report.append("")
    max_report_size = 15000  # Leave some buffer for Gerrit's 16384 limit
    current_size = sum(len(line) + 1 for line in report)

    if functional_changes:
        report.append("#### Functional Changes")
        report.append("| Board | Status | Diff |")
        report.append("| :--- | :--- | :--- |")
        current_size += sum(len(line) + 1 for line in report[-3:])

        added_rows = 0
        for row in functional_changes:
            row_len = len(row) + 1
            if current_size + row_len + 100 > max_report_size:
                break
            report.append(row)
            current_size += row_len
            added_rows += 1

        if added_rows < len(functional_changes):
            report.append(
                f"| ... | and {len(functional_changes) - added_rows} more | |"
            )
            current_size += len(report[-1]) + 1
        report.append("")
        current_size += 1

    if other_changes:
        header_lines = [
            "<details>",
            f"<summary>Non-functional changes to {len(other_changes)} "
            "other configurations</summary>",
            "",
            "| Affected Configuration | Status | Details |",
            "| :--- | :--- | :--- |",
        ]

        if (
            current_size + sum(len(line) + 1 for line in header_lines) + 200
            < max_report_size
        ):
            report.extend(header_lines)
            current_size += sum(len(line) + 1 for line in header_lines)

            added_other_rows = 0
            for row in other_changes:
                row_len = len(row) + 1
                if current_size + row_len + 100 > max_report_size:
                    break
                report.append(row)
                current_size += row_len
                added_other_rows += 1

            if added_other_rows < len(other_changes):
                report.append(
                    f"| ... | and {len(other_changes) - added_other_rows} more | |"
                )

            report.append("</details>")
            report.append("")

    if os.path.exists(main_diff_path):
        report.append("#### Full Processed Diff")
        report.append(
            "The full diff of processed XML files is available in the main.diff file."
        )

    if args.full_html_report:
        html = [
            "<!DOCTYPE html>",
            "<html><head><title>Servo XML Impact Full Report</title>",
            "<style>",
            "body { font-family: sans-serif; margin: 20px; }",
            "table { border-collapse: collapse; width: 100%; "
            "max-width: 800px; margin-bottom: 20px; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; }",
            "</style>",
            "</head><body>",
            "<h1>Servo XML Impact Full Report</h1>",
            f"<p>This change affects <strong>{len(func_data)}</strong> "
            "configurations functionally.</p>",
        ]

        if func_data:
            html.append("<h2>Functional Changes</h2>")
            html.append("<table><tr><th>Board</th><th>Status</th><th>Diff</th></tr>")
            for board, status, diff_html in func_data:
                html.append(
                    f"<tr><td>{board}</td><td>{status}</td><td>{diff_html}</td></tr>"
                )
            html.append("</table>")

        if other_data:
            html.append(f"<h2>Non-functional Changes ({len(other_data)})</h2>")
            html.append("<table><tr><th>Board</th><th>Status</th></tr>")
            for board, status in other_data:
                html.append(f"<tr><td>{board}</td><td>{status}</td></tr>")
            html.append("</table>")

        html.append("</body></html>")

        with open(args.full_html_report, "w", encoding="utf-8") as f:
            f.write("\n".join(html))

    if args.output_report:
        report_str = "\n".join(report) + "\n"
        with open(args.output_report, "w", encoding="utf-8") as f:
            f.write(report_str)

    # Cleanup
    shutil.rmtree(before_base)
    shutil.rmtree(after_base)
    shutil.rmtree(temp_out_dir)


if __name__ == "__main__":

    main()
