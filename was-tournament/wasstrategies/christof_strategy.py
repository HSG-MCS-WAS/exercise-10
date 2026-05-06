"""Christof's strategy for the WAS Axelrod Tournament.

Strategy: Cautious-Cooperator with Latch and Last-Round Defection (CCLLRD).

Tournament parameters (from README):
- 10 rounds per match (very short — end-game effects matter)
- Round-robin; each player also paired with own twin and Random(0.5)
- Five baselines: TitForTat, Grudger, Defector, Cooperator, Random(0.5)
- Plus auto-discovered student strategies and LLM variants
- Payoff (signed prison-years; higher is better):
    C/C: -1 / -1     R = -1 (mutual cooperation)
    C/D: -5 /  0     S = -5 (sucker)
    D/C:  0 / -5     T =  0 (temptation)
    D/D: -3 / -3     P = -3 (mutual defection)

Design rationale:
- Open with C: enables mutual cooperation with TitForTat / Grudger / Cooperator
  and any student strategies that mirror or reciprocate. Cost vs Defector is
  only 2 points (-32 vs -30 across the match) — cheap insurance.
- Last-round D (round 10 only): strict Pareto-improvement against any opponent
  that does not also defect in the last round. Defecting on round 9 unravels
  the cooperation chain and yields strictly worse outcomes against every TFT
  variant; defecting only on round 10 is the safe end-game move.
- Opening-defection tell: if the opponent defects on round 1, classify as
  hostile (Defector / ALL-D) and switch to permanent D for the rest of the
  match.
- Heavy-defection threshold: after 3+ rounds, if the opponent has defected
  >= 50% of the time, treat as Random or aggressive and switch to permanent D.
- Latch on first own defection: once we have ever defected in a match, we keep
  defecting until end-game. Prevents oscillation against Random and prevents
  re-exploitation by toggling opponents. Forgiveness against truly noisy nice
  opponents is sacrificed for robustness in a 10-round window.
- The result is a strategy that is nice, retaliatory, clear, and exploits the
  finite horizon without unraveling.
"""

from axelrod.action import Action
from axelrod.player import Player

C, D = Action.C, Action.D


class Christof(Player):
    name = "WAS - Christof"
    classifier = {
        "memory_depth": float("inf"),
        "stochastic": False,
        "long_run_time": False,
        "inspects_source": False,
        "manipulates_source": False,
        "manipulates_state": False,
    }

    def strategy(self, opponent: Player) -> Action:
        n = len(self.history)

        if n == 0:
            return C

        if n == 9:
            return D

        if self.defections > 0:
            return D

        if opponent.history[0] == D:
            return D

        if n >= 3 and opponent.defections / n >= 0.5:
            return D

        return opponent.history[-1]
