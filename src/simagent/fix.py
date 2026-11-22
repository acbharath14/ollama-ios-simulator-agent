"""Apply one model-proposed single-file fix. Dry run is the default.

Rules: the working tree must be clean, the diff must validate with
git apply --check, nothing is committed, nothing is merged, and --apply
is required to write anything.
"""

import difflib
import re
import subprocess


class FixError(Exception):
    pass


def extract_file(text):
    """Pull the full corrected file out of model output, fenced or raw."""
    match = re.search(r"```\w*\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text


def compute_diff(file_path, original, new):
    """Build a unified diff from the original to the new file contents.

    The diff is computed by the tool, never hand-written by the model, so
    its context lines always match the file exactly.
    """
    orig_lines = original.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff_lines = difflib.unified_diff(
        orig_lines,
        new_lines,
        fromfile="a/" + file_path,
        tofile="b/" + file_path,
    )
    return "".join(diff_lines)


def has_hunks(diff):
    return bool(re.search(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@", diff, re.MULTILINE))


def check_clean_tree(repo_dir):
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise FixError("not a git repository or git failed: %s" % repo_dir)
    if proc.stdout.strip():
        raise FixError("working tree is dirty; commit or stash changes first")


def validate_diff(repo_dir, diff):
    if not has_hunks(diff):
        raise FixError("no diff hunks found in model output")
    proc = subprocess.run(
        ["git", "apply", "--check", "-"],
        input=diff,
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise FixError("diff does not apply cleanly: %s" % proc.stderr.strip())
    return True


def apply_fix(repo_dir, diff, dry_run=True):
    """Validate the diff, then apply it only when dry_run is False."""
    check_clean_tree(repo_dir)
    validate_diff(repo_dir, diff)
    if dry_run:
        return "dry-run: diff validated, nothing written"
    proc = subprocess.run(
        ["git", "apply", "-"],
        input=diff,
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise FixError("git apply failed: %s" % proc.stderr.strip())
    return "applied: working tree updated, nothing committed"
