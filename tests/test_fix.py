import subprocess

import pytest

from simagent import fix

GOOD_DIFF = """--- a/hello.txt
+++ b/hello.txt
@@ -1 +1 @@
-hello
+hello world
"""

FENCED_DIFF = "Here is the fix:\n```diff\n" + GOOD_DIFF + "```\n"


def _init_repo(path):
    def git(*args, **kwargs):
        subprocess.run(
            ["git", "-C", str(path), "-c", "user.email=a@b.c", "-c", "user.name=t", *args],
            check=True,
            capture_output=True,
            text=True,
            **kwargs,
        )

    git("init")
    (path / "hello.txt").write_text("hello\n", encoding="utf-8")
    git("add", "hello.txt")
    git("commit", "-m", "initial")
    return git


def test_extract_diff_fenced():
    assert fix.extract_diff(FENCED_DIFF) == GOOD_DIFF


def test_extract_diff_raw():
    assert fix.extract_diff(GOOD_DIFF) == GOOD_DIFF


def test_has_hunks():
    assert fix.has_hunks(GOOD_DIFF) is True
    assert fix.has_hunks("no hunks here") is False
    assert fix.has_hunks("@@ -1 +1 @@\n-x\n+y\n") is True


def test_validate_diff_good(tmp_path):
    _init_repo(tmp_path)
    assert fix.validate_diff(str(tmp_path), GOOD_DIFF) is True


def test_validate_diff_bad(tmp_path):
    _init_repo(tmp_path)
    bad = GOOD_DIFF.replace("-hello", "-not in file")
    with pytest.raises(fix.FixError, match="does not apply cleanly"):
        fix.validate_diff(str(tmp_path), bad)


def test_validate_diff_no_hunks(tmp_path):
    _init_repo(tmp_path)
    with pytest.raises(fix.FixError, match="no diff hunks"):
        fix.validate_diff(str(tmp_path), "nothing here")


def test_apply_fix_dry_run_writes_nothing(tmp_path):
    _init_repo(tmp_path)
    result = fix.apply_fix(str(tmp_path), GOOD_DIFF, dry_run=True)
    assert "dry-run" in result
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hello\n"


def test_apply_fix_writes_and_does_not_commit(tmp_path):
    _init_repo(tmp_path)
    result = fix.apply_fix(str(tmp_path), GOOD_DIFF, dry_run=False)
    assert "applied" in result
    assert (tmp_path / "hello.txt").read_text(encoding="utf-8") == "hello world\n"
    log = subprocess.run(
        ["git", "-C", str(tmp_path), "log", "--oneline"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert len(log.stdout.strip().splitlines()) == 1


def test_apply_fix_refuses_dirty_tree(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "hello.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(fix.FixError, match="dirty"):
        fix.apply_fix(str(tmp_path), GOOD_DIFF, dry_run=True)


def test_apply_fix_not_a_repo(tmp_path):
    with pytest.raises(fix.FixError, match="not a git repository"):
        fix.apply_fix(str(tmp_path), GOOD_DIFF, dry_run=True)
