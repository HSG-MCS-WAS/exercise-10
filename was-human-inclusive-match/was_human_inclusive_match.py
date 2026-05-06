"""Code adapted from https://axelrod.readthedocs.io/en/stable/tutorials/new_to_game_theory_and_or_python/human_interaction.html

axelrod 4.14.0 dropped the Human strategy from the package, so we import a
vendored copy from human_strategy.py instead of axl.Human.
"""

import axelrod as axl

from human_strategy import Human

# Human's name
me = Human(name='me')

# The players are me and a TitForTat player
players = (axl.TitForTat(), me)

# Create a match between players with 3 turns
match = axl.Match(players, turns=3)

# Play the match
match.play() 

# Print results (coerce numpy int64 scores to plain ints for nicer output)
scores_per_turn = [(int(a), int(b)) for a, b in match.scores()]
final_score = tuple(int(x) for x in match.final_score())

print(f"Match winner: {match.winner()}")
print(f"Match scores per turn: {scores_per_turn}")
print(f"Match final score: {final_score}")
