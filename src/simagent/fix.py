"""Apply one model-proposed single-file fix. Dry run is the default.

Rules: the working tree must be clean, the diff must validate with
git apply --check, nothing is committed, nothing is merged, and --apply
is required to write anything.
"""

import re
import subprocess


class FixError(Exception):
    pass


def extract_diff(text):
    """Pull a unified diff out of model output, fenced or raw."""
    match = re.search(r"```(?:diff)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip() + "\n"
    return text.strip() + "\n"


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
