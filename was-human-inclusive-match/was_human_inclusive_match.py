"""Code retrieved from https://axelrod.readthedocs.io/en/stable/tutorials/new_to_game_theory_and_or_python/human_interaction.html"""

import axelrod as axl

# Human's name
me = axl.Human(name='me')

# The players are me and a TitForTat player
players = (axl.TitForTat(), me)

# Create a match between players with 3 turns
match = axl.Match(players, turns=3)

# Play the match
match.play() 

# Print results
print(f"Match winner: {match.winner()}")
print(f"Match scores per turn: {match.scores()}")
print(f"Match final score: {match.final_score()}")
