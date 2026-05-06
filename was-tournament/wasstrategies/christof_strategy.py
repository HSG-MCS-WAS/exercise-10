"""Christof's strategy for the WAS Axelrod Tournament.

Strategy: Latched Tit-for-Tat with Two-Round End-Game Defection.

Tournament parameters (from README):
- 10 rounds per match (very short — end-game effects matter)
- Round-robin; each player also paired with own twin and Random(0.5)
- Five baselines: TitForTat, Grudger, Defector, Cooperator, Random(0.5)
- Plus auto-discovered student strategies (LLM-coached, mostly)
- Payoff (signed prison-years; higher is better):
    C/C: -1 / -1     R = -1 (mutual cooperation)
    C/D: -5 /  0     S = -5 (sucker)
    D/C:  0 / -5     T =  0 (temptation)
    D/D: -3 / -3     P = -3 (mutual defection)

Field assumption (calibrated to the WAS tournament):
- ~80% of student strategies are LLM-coached and will include some end-game
  defection (last 1-2 rounds is the most common LLM recommendation).
- Pure TFT / pure Grudger appear only as the two baselines; rare among student
  submissions.

Design rationale (six rules, evaluated top to bottom):
1. Round 1 → C. Enables mutual cooperation with every TFT-variant and pays
   only -2 vs Defector (-32 vs -30) — cheap insurance.
2. Rounds 9-10 (n>=8) → D. Two-round end-game. Against any opponent who also
   defects in round 9 (likely in this field), R9 D prevents being exploited
   for -5; against pure-TFT / pure-Grudger it costs 2 points but those are
   minority. Going further to round 8 costs more than it gains.
3. Once we have defected → D. Latch prevents oscillation against Random and
   re-exploitation by toggling opponents. In a 10-round window, forgiveness
   does not pay back its cost.
4. Opening-defection tell → D. Opponent's R1 D is a strong Defector / ALL-D
   signal. Permanent D from R2.
5. Heavy-defection threshold (>=50% defects after 3+ rounds) → D. Catches
   Random and aggressive opponents whose first move was C.
6. Default → Tit-for-Tat. Mirror opponent's last move.
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

        if n >= 8:
            return D

        if self.defections > 0:
            return D

        if opponent.history[0] == D:
            return D

        if n >= 3 and opponent.defections / n >= 0.5:
            return D

        return opponent.history[-1]
