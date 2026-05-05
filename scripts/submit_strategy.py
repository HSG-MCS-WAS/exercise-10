"""Submit a student strategy as a Pull Request to main.

Run this from the VS Code "Submit Strategy as PR" launch configuration, or via:
    uv run python scripts/submit_strategy.py

What it does:
  1. Finds the student's strategy file under was-tournament/wasstrategies/
     (any *_strategy.py that isn't sample_strategy.py and isn't already on main).
  2. Creates a new branch named <name>-strategy.
  3. Commits the strategy file.
  4. Pushes the branch and opens a Pull Request to main using `gh`.

Requirements:
  - `git` and `gh` (GitHub CLI) on PATH. In Codespaces both are preinstalled and
    `gh` is already authenticated.
  - You've added exactly one new *_strategy.py file under was-tournament/wasstrategies/.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGIES_DIR = REPO_ROOT / "was-tournament" / "wasstrategies"


def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=check,
        text=True,
        capture_output=capture,
    )
    if capture and result.stdout:
        print(result.stdout, end="")
    return result


def find_student_strategy() -> Path:
    """Locate the single student-authored *_strategy.py the user wants to submit."""
    tracked_on_main = set()
    try:
        out = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "origin/main", "was-tournament/wasstrategies/"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout
        tracked_on_main = {REPO_ROOT / line.strip() for line in out.splitlines() if line.strip()}
    except subprocess.CalledProcessError:
        print("warning: could not list files on origin/main; falling back to local-only detection")

    candidates: list[Path] = []
    for path in sorted(STRATEGIES_DIR.glob("*_strategy.py")):
        if path.name == "sample_strategy.py":
            continue
        if path in tracked_on_main:
            continue
        candidates.append(path)

    if not candidates:
        print(
            "ERROR: no new strategy file found under was-tournament/wasstrategies/.\n"
            "Copy sample_strategy.py to <your_name>_strategy.py first, edit it,\n"
            "then re-run this script."
        )
        sys.exit(1)
    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        print(
            f"ERROR: found multiple new strategy files ({names}).\n"
            "This script expects exactly one new *_strategy.py file. Remove the\n"
            "extras (or commit them separately) and re-run."
        )
        sys.exit(1)
    return candidates[0]


def derive_student_name(strategy_path: Path) -> str:
    """`urs_strategy.py` -> `urs`."""
    return strategy_path.stem.removesuffix("_strategy")


def ensure_clean_or_only_strategy(strategy_path: Path) -> None:
    """Make sure the only uncommitted change is the strategy file itself."""
    out = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    dirty = []
    rel = strategy_path.relative_to(REPO_ROOT).as_posix()
    for line in out.splitlines():
        path = line[3:].strip()
        if path != rel:
            dirty.append(line)
    if dirty:
        print(
            "ERROR: working tree has changes beyond your strategy file:\n"
            + "\n".join(f"  {d}" for d in dirty)
            + "\n\nPlease stash, revert, or commit those changes separately."
        )
        sys.exit(1)


def main() -> int:
    strategy_path = find_student_strategy()
    name = derive_student_name(strategy_path)
    branch = f"{name}-strategy"
    rel = strategy_path.relative_to(REPO_ROOT).as_posix()

    print(f"Found strategy file: {rel}")
    print(f"Will submit as branch '{branch}' and open a PR to main.\n")

    ensure_clean_or_only_strategy(strategy_path)

    # Make sure we have an up-to-date main reference.
    run(["git", "fetch", "origin", "main"])

    # Create or switch to the submission branch.
    existing = subprocess.run(
        ["git", "rev-parse", "--verify", branch],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if existing.returncode == 0:
        run(["git", "checkout", branch])
    else:
        run(["git", "checkout", "-b", branch, "origin/main"])

    run(["git", "add", rel])

    # Commit (skip if nothing staged, e.g. re-running after a successful commit).
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=REPO_ROOT,
        check=False,
    )
    if diff.returncode != 0:
        run(["git", "commit", "-m", f"Add {name} strategy"])
    else:
        print("(nothing new to commit)")

    run(["git", "push", "-u", "origin", branch])

    # Open the PR. If one already exists for this branch, `gh pr create` errors;
    # fall back to viewing the existing PR.
    pr = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            f"Add {name} strategy",
            "--body",
            f"Submitting {name}'s strategy for the WAS Axelrod tournament.",
        ],
        cwd=REPO_ROOT,
        text=True,
    )
    if pr.returncode != 0:
        print("\n`gh pr create` failed (likely because a PR already exists). Showing it:")
        run(["gh", "pr", "view", "--web"], check=False)
    else:
        run(["gh", "pr", "view", "--web"], check=False)

    print("\nDone. Check the GitHub PR page that just opened.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
