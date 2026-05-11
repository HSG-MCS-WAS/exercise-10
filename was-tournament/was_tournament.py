import argparse
import importlib
import inspect
import pkgutil

import axelrod as axl
from axelrod.player import Player

import wasstrategies


LLM_SUBPACKAGE = f"{wasstrategies.__name__}.llm_variants"


def discover_student_players(include_llm: bool = True):
    players = []
    for module_info in pkgutil.walk_packages(
        wasstrategies.__path__, prefix=f"{wasstrategies.__name__}."
    ):
        if module_info.ispkg:
            continue
        if not include_llm and module_info.name.startswith(LLM_SUBPACKAGE + "."):
            continue
        module = importlib.import_module(module_info.name)
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ == module.__name__ and issubclass(cls, Player):
                players.append(cls())
    players.sort(key=lambda p: p.name)
    return players


parser = argparse.ArgumentParser(
    description="Run the WAS Axelrod tournament. "
    "By default, includes the five built-in baselines plus every "
    "auto-discovered strategy under wasstrategies/ (including the "
    "llm_variants sub-package)."
)
mode = parser.add_mutually_exclusive_group()
mode.add_argument(
    "--builtin-only",
    action="store_true",
    help="Run only the built-in baselines (Cooperator, Defector, TitForTat, "
    "Grudger, Random); skip the wasstrategies/ discovery. Output files are "
    "suffixed with '_builtin' so they don't overwrite a full run.",
)
mode.add_argument(
    "--no-llm",
    action="store_true",
    help="Skip strategies under wasstrategies/llm_variants/ but still include "
    "the five built-in baselines and the top-level student strategies. "
    "Output files are suffixed with '_no_llm'.",
)
parser.add_argument(
    "--runs",
    type=int,
    default=1,
    help="Number of tournament repetitions to run. Axelrod plays every "
    "match this many times and aggregates scores, wins, and morality "
    "metrics (means across runs). Default: 1.",
)
args = parser.parse_args()
if args.runs < 1:
    parser.error("--runs must be >= 1")

builtin_strategies = [
    axl.Cooperator(),
    axl.Defector(),
    axl.TitForTat(),
    axl.Grudger(),
    axl.Random(0.5),
]
strategies = list(builtin_strategies)
if not args.builtin_only:
    strategies.extend(discover_student_players(include_llm=not args.no_llm))

if args.builtin_only:
    suffix = "_builtin"
elif args.no_llm:
    suffix = "_no_llm"
else:
    suffix = ""
csv_path = f"was_tournament_analysis{suffix}.csv"
results_png = f"was_results{suffix}.png"
wins_png = f"was_win_distributions{suffix}.png"
payoff_png = f"was_payoff_matrix{suffix}.png"

# Print the strategy players
print(f"Available strategies: {strategies}")

# Play on the prisoner's dilemma: a = -1, b = -5, c = 0, d = -3
prisoners_dilemma = axl.game.Game(r=-1, s=-5, t=0, p=-3)

# Create the tournament between strategy players with 10 turns.
# `repetitions` re-plays every match N times; results.scores, wins,
# and morality metrics are aggregated (means) across the N runs.
print(f"Running tournament with {args.runs} repetition(s).")
tournament = axl.Tournament(
    strategies, game=prisoners_dilemma, turns=10, repetitions=args.runs
)

# Play the tournament
results = tournament.play(filename=csv_path)

# Print the players from the best to the worst
print(f"\nRanked results: {results.ranked_names}\n")


"""Visualize interactions (https://axelrod.readthedocs.io/en/stable/tutorials/new_to_game_theory_and_or_python
/visualising_results.html)"""
plot = axl.Plot(results)

# View the scores averaged per opponent and turns
p1 = plot.boxplot()
p1.show()
p1.savefig(results_png)

# View the distributions of wins for each strategy
p2 = plot.winplot()
p2.show()
p2.savefig(wins_png)

# View the payoff matrix
p2 = plot.payoff()
p2.show()
p2.savefig(payoff_png)


"""Morality metrics (https://axelrod.readthedocs.io/en/latest/how-to/calculate_morality_metrics.html#morality-metrics
)"""

print("--- Morality Metrics ---")
for i in range(0, len(strategies)):
    print(strategies[i], ":")
    print(f"Cooperating rating: {round(results.cooperating_rating[i], 2)}")
    print(f"Good partner rating: {round(results.good_partner_rating[i], 2)}")
    print(f"Eigen Jesus rating: {round(results.eigenjesus_rating[i], 2)}")
    print(f"Eigen Moses rating: {round(results.eigenmoses_rating[i], 2)}\n")
