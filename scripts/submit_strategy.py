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


def _git_ignored(paths: list[Path]) -> set[Path]:
    """Return the subset of `paths` that git ignores (per .gitignore)."""
    if not paths:
        return set()
    rels = [p.relative_to(REPO_ROOT).as_posix() for p in paths]
    # `git check-ignore` exits 0 if any path is ignored, 1 if none are, >1 on error.
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--", *rels],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode not in (0, 1):
        print(f"warning: `git check-ignore` failed: {result.stderr.strip()}")
        return set()
    ignored_rels = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return {REPO_ROOT / r for r in ignored_rels}


def find_student_strategy() -> Path:
    """Locate the single student-authored *_strategy.py the user wants to submit.

    A file counts as student-authored when it is NOT gitignored and NOT the
    sample. This excludes the LLM-generated reference strategies (which are
    listed individually in .gitignore) without requiring any network access.
    """
    all_strategies = [
        p for p in sorted(STRATEGIES_DIR.glob("*_strategy.py"))
        if p.name != "sample_strategy.py"
    ]
    ignored = _git_ignored(all_strategies)

    candidates = [p for p in all_strategies if p not in ignored]

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


# Files that are commonly auto-generated and that students rarely want to commit.
# When one of these shows up as dirty we suggest gitignoring it instead of staging it.
KNOWN_GENERATED_FILES = {
    ".devcontainer/devcontainer-lock.json",
}


def ensure_clean_or_only_strategy(strategy_path: Path) -> None:
    """Make sure the only uncommitted change is the strategy file itself."""
    out = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    rel = strategy_path.relative_to(REPO_ROOT).as_posix()

    tracked: list[str] = []   # modified/added/deleted/renamed tracked files
    untracked: list[str] = []  # `??` entries
    for line in out.splitlines():
        # Porcelain format: "XY path" — XY is 2 status chars, then a space, then the path.
        status, path = line[:2], line[3:].strip()
        if path == rel:
            continue
        if status == "??":
            untracked.append(path)
        else:
            tracked.append(path)

    if not tracked and not untracked:
        return

    lines = ["ERROR: working tree has changes beyond your strategy file.", ""]

    if tracked:
        lines.append("Tracked files with uncommitted edits:")
        lines.extend(f"  {p}" for p in tracked)
        lines.append("")
        lines.append("  To set them aside temporarily:")
        lines.append("      git stash push -- " + " ".join(tracked))
        lines.append("  Or to commit them on a separate branch first:")
        lines.append("      git checkout -b my-other-changes && git add <files> && git commit")
        lines.append("")

    if untracked:
        lines.append("Untracked files that would also be left behind:")
        lines.extend(f"  {p}" for p in untracked)
        lines.append("")
        lines.append("  To stash them along with tracked changes, use `git stash -u`.")
        lines.append("  To delete them, use `git clean -f -- <path>` (irreversible).")
        lines.append("")

    generated_present = sorted(set(tracked + untracked) & KNOWN_GENERATED_FILES)
    if generated_present:
        lines.append(
            "Note: the following files look auto-generated and are usually safe to add to .gitignore:"
        )
        lines.extend(f"  {p}" for p in generated_present)
        lines.append("")

    lines.append("Re-run this script once your working tree shows only the strategy file.")
    print("\n".join(lines))
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
