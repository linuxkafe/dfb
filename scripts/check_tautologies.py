#!/usr/bin/env python3
"""Tautology gate — reject always-true / always-false assertion anti-patterns.

Catches test-corruption edits of the class that shipped in commit 82fe68f:

    assert "correlation_id" in call_kwargs or True

The `or True` makes an assertion unconditional: the gate goes green while
the test becomes a no-op. This script scans the same scope as `lint-check`
(`src tests`) and fails (exit 1) on any blacklisted pattern.

Intent:
- Blocking, unlike `code-check`'s `grep ... || true`.
- Each hit prints file:line:code so a human can adjudicate a false
  positive rather than silently deleting the gate.
- Regex-based by design: empirically the common shapes are what ship. An
  AST semantic checker would be stronger but adds tool coupling for a
  low-hazard class of bug.

Usage:
    python3 scripts/check_tautologies.py [paths...]   (default: src tests)
    python3 scripts/check_tautologies.py --selftest   (prove the gate works)

Exit: 0 = clean, 1 = at least one blacklisted pattern found (or --selftest
failed to detect a planted pattern).
"""

import os
import shutil
import sys
import tempfile

PATTERNS = [
    ("assert ... or True", r"assert\s+.*?\bor\s+True\b"),
    ("assert True", r"assert\s+True\b"),
    ("assert ... and False", r"assert\s+.*?\band\s+False\b"),
    ("assert False", r"assert\s+False\b"),
    ("self-comparison", r"assert\s+(\w+(?:\.\w+)?)\s*[=<>]=?\s*\1\b"),
    ("literal tautology", r"assert\s+(?:1\s*==\s*1|0\s*==\s*0)\b"),
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    "dist",
    "build",
}


def _iter_python_files(scopes):
    for scope in scopes:
        path = os.path.join(ROOT, scope) if not os.path.isabs(scope) else scope
        if os.path.isfile(path):
            if path.endswith(".py"):
                yield path
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if name.endswith(".py"):
                    yield os.path.join(dirpath, name)


def scan(scopes):
    """Return (failures, total_files). failure = (relpath, lineno, code)."""
    failures = []
    total_files = 0
    for path in _iter_python_files(scopes):
        rel = os.path.relpath(path, ROOT)
        total_files += 1
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for name, regex in PATTERNS:
            for lineno, line in enumerate(lines, start=1):
                if _match(regex, line):
                    failures.append((rel, lineno, line.strip(), name))
    return failures, total_files


def _match(regex, line):
    import re

    # Strip comments from the line to avoid flagging prose that merely
    # *mentions* the pattern (e.g. a comment explaining why we forbid it).
    code = line.split("#", 1)[0]
    return re.search(regex, code, re.MULTILINE) is not None


def _selftest():
    """Plant one instance of each pattern and assert the gate catches it."""
    planted = [
        ('assert "cid" in kwargs or True', "assert ... or True"),
        ("assert True", "assert True"),
        ("assert ready and False", "assert ... and False"),
        ("assert False", "assert False"),
        ("assert x == x", "self-comparison"),
        ("assert 1 == 1", "literal tautology"),
    ]
    clean_tmp = None
    try:
        tmp = tempfile.mkdtemp(prefix="tautology-selftest-")
        bad = os.path.join(tmp, "bad.py")
        clean = os.path.join(tmp, "clean.py")
        with open(bad, "w", encoding="utf-8") as fh:
            body = "\n".join(
                f"def t{i}():\n    {code}\n" for i, (code, _) in enumerate(planted)
            )
            fh.write(body)
        with open(clean, "w", encoding="utf-8") as fh:
            fh.write("def ok():\n    assert value == expected\n")
        failures, _ = scan([tmp])
        detected = {name for _, _, _, name in failures}
        missing = [expected for _, expected in planted if expected not in detected]
        if missing:
            print(f"SELFTEST FAIL: patterns not detected: {missing}")
            return 1
        print(
            f"SELFTEST OK: all {len(planted)} patterns detected"
            f" ({len(failures)} hits across {len(planted)} lines)."
        )
        return 0
    finally:
        if clean_tmp is not None:
            shutil.rmtree(clean_tmp, ignore_errors=True)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--selftest" in argv:
        return _selftest()

    scopes = [a for a in argv if not a.startswith("-")] or ["src", "tests"]
    failures, total_files = scan(scopes)
    if failures:
        print(
            f"FAIL: {len(failures)} tautolog(ies) found in {total_files} files scanned."
        )
        for rel, lineno, code, name in failures:
            print(f"  {rel}:{lineno}: [{name}] {code}")
        print(
            "Always-true / always-false assertions make tests unconditional and turn "
            "green gates into no-ops. Rewrite the assertion to check the real value, "
            "or flag the line explicitly if the pattern is intentional."
        )
        return 1
    print(
        f"tautology-check: OK ({total_files} files scanned, no always-true assertions)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
