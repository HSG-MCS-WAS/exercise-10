# WAS Axelrod Tournament

Main repository for the Axelrod Tournament of the Web-based Autonomous Systems course at the University of St. Gallen. It uses the [Axelrod 4.14.0 Python library](https://pypi.org/project/Axelrod/) and is hosted at <https://github.com/HSG-MCS-WAS/exercise-10>.

## Table of Contents
-   [Quick start (for students)](#quick-start-for-students)
-   [How to install Axelrod](#how-to-install-axelrod)
-   [Running the scripts in VS Code](#running-the-scripts-in-vs-code)
-   [WAS Axelrod Tournament Rules](#was-axelrod-tournament-rules)
-   [How to prepare for the WAS Axelrod Tournament](#how-to-prepare-for-the-was-axelrod-tournament)
    1. [Run a simple tournament](#run-a-simple-tournament)
    2. [Play as a human to explore different strategies](#play-as-a-human-to-explore-different-strategies)
    3. [Implement and submit your own strategy](#implement-and-submit-your-own-strategy)

## Quick start (for students)

You have two options: open the repo in **GitHub Codespaces** (zero setup) or clone it **locally**.

### Option A — GitHub Codespaces (recommended, no setup)

1. On the repo's GitHub page click **Code → Codespaces → Create codespace on main**.
2. Wait ~1 min while the dev container builds and `uv sync` runs automatically.
3. Skip to step 4 below.

### Option B — Local clone

1. **Clone the repository**
   ```
   git clone https://github.com/HSG-MCS-WAS/exercise-10.git
   cd exercise-10
   ```
2. **Install dependencies** with `uv` (see [How to install Axelrod](#how-to-install-axelrod)):
   ```
   uv sync
   ```
3. **Open the project in VS Code** and let it pick up the `.venv` interpreter automatically (configured in [.vscode/settings.json](.vscode/settings.json)).

### Then, regardless of A or B

4. **Write your strategy**: copy [was-tournament/wasstrategies/sample_strategy.py](was-tournament/wasstrategies/sample_strategy.py) to `was-tournament/wasstrategies/<your_name>_strategy.py` and adapt the class (rename it from `Example` to e.g. `Urs`, change `name = "..."`, and rewrite the `strategy` method). The tournament runner auto-discovers every `axelrod.Player` subclass in that directory — no edits to `was_tournament.py` needed.
5. **Run the tournament locally** from the VS Code **Run and Debug** view → **Run WAS Tournament** (see [Running the scripts in VS Code](#running-the-scripts-in-vs-code)). Confirm your strategy appears in the printed `Available strategies` list and in the resulting plots / CSV.
6. **Submit your strategy** by running **Run and Debug → Submit Strategy as PR**. This automatically:
    - creates a new branch `<your_name>-strategy` off `origin/main`,
    - commits your `*_strategy.py` file,
    - pushes the branch,
    - opens a Pull Request against `main` using the GitHub CLI (`gh`).

   In Codespaces, `gh` is already authenticated. Locally, run `gh auth login` once first.

## How to install Axelrod

This repo is managed with [uv](https://docs.astral.sh/uv/). It targets Python 3.11–3.12 and pins `axelrod==4.14.0`.

### Codespaces / Dev Container
Open the repo in GitHub Codespaces or "Reopen in Container" in VS Code. The dev container in [`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json) installs `uv` and runs `uv sync` automatically.

### Local
Install `uv` (one-time):
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Then from the repo root:
```
uv sync
uv run python was-tournament/was_tournament.py
```
`uv sync` creates a `.venv` and installs all pinned dependencies from [`pyproject.toml`](pyproject.toml) / `uv.lock`.

## Running the scripts in VS Code

The repo ships with [.vscode/launch.json](.vscode/launch.json) so both scripts can be run directly from the VS Code **Run and Debug** view (the ▶️ icon in the left sidebar, or `Cmd+Shift+D` / `Ctrl+Shift+D`).

1. Make sure you ran `uv sync` once so `.venv/bin/python` exists.
2. Open the **Run and Debug** view.
3. Pick one of the configurations from the dropdown at the top:
    - **Run WAS Tournament** → runs [was-tournament/was_tournament.py](was-tournament/was_tournament.py) (the round-robin tournament with all auto-discovered strategies).
    - **Run WAS Tournament (builtin only)** → same script with `--builtin-only`: only the five Axelrod baselines, output files suffixed `_builtin`.
    - **Run WAS Tournament (no LLM)** → same script with `--no-llm`: baselines + top-level student strategies, skipping `wasstrategies/llm_variants/`; output files suffixed `_no_llm`.
    - **Play Human-Inclusive Match** → runs [was-human-inclusive-match/was_human_inclusive_match.py](was-human-inclusive-match/was_human_inclusive_match.py) (play interactively against a `TitForTat` opponent).
    - **Submit Strategy as PR** → runs [scripts/submit_strategy.py](scripts/submit_strategy.py): creates a new branch `<your_name>-strategy`, commits your `*_strategy.py`, pushes it, and opens a PR to `main` via the GitHub CLI (`gh`). Codespaces has `gh` preauthenticated; locally run `gh auth login` once.
4. Click the green ▶️ play button (or press `F5` to debug, `Ctrl+F5` to run without debugging).

The Python extension (`ms-python.python`) must be installed — it usually is by default.

## WAS Axelrod Tournament Rules
Each player submits their strategy for the Prisoner's Dilemma. The tournament is a round robin run (one iteration) so that each player is paired with every other player. 
Each player is also paired with its own twin and with RANDOM, a strategy player that cooperates or defects in each round with equal probability. 
Each match between two players consists of 10 rounds.
The player whose strategy accumulated the greatest score wins.

Scores are attributed based on the Prisoner's Dilemma where each player has two possible actions, Cooperate (C), and Defect(D). The following negative payoffs indicate how many years each player will spend in prison (in absolute value):

|               | Cooperate (C) | Defect (D) |
|:-------------:|:-------------:|:----------:|
| Cooperate (C) |    (-1,-1)    |   (-5,0)   |
|   Defect (D)  |    (0,-5)     |   (-3,-3)  |


## How to prepare for the WAS Axelrod Tournament
### Run a simple tournament
Run `uv run python was-tournament/was_tournament.py` ([was_tournament.py](/was-tournament/was_tournament.py)) to run a 10-round, single round-robin tournament between:

- the five Axelrod baselines: `TitForTat`, `Grudger` (i.e. a Trigger), `Defector`, `Cooperator`, and `Random(0.5)`,
- every student strategy at the top level of `was-tournament/wasstrategies/` (auto-discovered — no edits to `was_tournament.py` needed),
- any committed strategies under sub-packages such as `was-tournament/wasstrategies/llm_variants/` (also auto-discovered recursively).

CLI flags (mutually exclusive):
- `--builtin-only`: run only the five baselines. Output files are suffixed with `_builtin`.
- `--no-llm`: include the baselines and top-level student strategies, but skip everything under `wasstrategies/llm_variants/`. Output files are suffixed with `_no_llm`.

Without either flag, all auto-discovered strategies (including LLM variants) are included.

The tournament produces four output files in `was-tournament/`:
- [was_results.png](./was-tournament/was_results.png): visualizes tournament normalized scores
- [was_win_distributions.png](./was-tournament/was_win_distributions.png): visualizes tournament win distributions
- [was_payoff_matrix.png](./was-tournament/was_payoff_matrix.png): visualizes tournament payoff matrix
- [was_tournament_analysis.csv](./was-tournament/was_tournament_analysis.csv): summarises tournament results

Additionally, the program prints the [morality metrics](https://axelrod.readthedocs.io/en/stable/how-to/calculate_morality_metrics.html) calculated for each player of the tournament:
- Cooperation Rate: The fraction of interactions in which the player cooperated.
- Good-Partner Rate: The fraction of interactions in which the player cooperated at least as much as its opponent (excluding interactions between a player and its own clone).
- Eigenjesus Rate: A metric that always favors cooperation, and gives more (positive) weight to cooperations with moral opponents than
to cooperations with immoral opponents.
- Eigenmoses Rate: A metric that favors cooperation with moral opponents, and defecting immoral oppontents. It gives a positive weight to cooperations with moral opponents, and a negative weight to cooperations with immoral opponents.

### Play as a human to explore different strategies
Before implementing your strategy, you can run `uv run python was-human-inclusive-match/was_human_inclusive_match.py` ([was_human_inclusive_match.py](/was-human-inclusive-match/was_human_inclusive_match.py)), and try out different strategies by
[playing as a human against a TitForTat player](https://axelrod.readthedocs.io/en/fix-documentation/tutorials/getting_started/human_interaction.html).

### Implement and submit your own strategy

**1. Add your strategy file**

Copy [sample_strategy.py](/was-tournament/wasstrategies/sample_strategy.py) to a new file `was-tournament/wasstrategies/<your_name>_strategy.py` and adapt it:
- The module name must follow the format `{your_name}_strategy.py` (e.g. `urs_strategy.py`).
- Your class name should follow the format `{Name}` (e.g. `class Urs(Player):`).
- Pick a unique `name = "..."` attribute so it shows up clearly in the results.

For background on writing Axelrod strategies, see the [official Axelrod tutorial](https://axelrod.readthedocs.io/en/fix-documentation/tutorials/contributing/strategy/writing_the_new_strategy.html), an [additional example strategy](https://github.com/Axelrod-Python/Axelrod/blob/75ef1f24187350292c43d244370c100c644748bc/docs/how-to/contributing/strategy/writing_the_new_strategy.rst) that considers the history of interactions, and [these variations for Tit-for-Tat](https://github.com/Axelrod-Python/Axelrod/blob/dev/axelrod/strategies/titfortat.py).

**2. Run the tournament locally**

The runner auto-discovers every `axelrod.Player` subclass in `was-tournament/wasstrategies/`, so dropping in a new `*_strategy.py` file is enough — no need to edit [was_tournament.py](/was-tournament/was_tournament.py). Run the tournament from VS Code's **Run and Debug → Run WAS Tournament** (see [Running the scripts in VS Code](#running-the-scripts-in-vs-code)) or via:
```
uv run python was-tournament/was_tournament.py
```
Confirm your strategy appears in the printed `Available strategies` list and in the resulting plots / CSV.

**3. Submit your strategy as a Pull Request**

In VS Code's **Run and Debug** view, pick **Submit Strategy as PR** and click ▶️. It runs [scripts/submit_strategy.py](scripts/submit_strategy.py), which automatically:

- creates a new branch `<your_name>-strategy` off `origin/main`,
- commits your `*_strategy.py` file (and only that file),
- pushes the branch,
- opens a Pull Request against `main` using the GitHub CLI.

In Codespaces `gh` is already authenticated. Locally, run `gh auth login` once first. The script will refuse to proceed if you have other uncommitted changes — please only commit your own `*_strategy.py` file (don't commit regenerated plots, CSVs, or other people's strategies).
