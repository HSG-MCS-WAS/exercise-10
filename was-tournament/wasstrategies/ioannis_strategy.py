"""Aggressive forgiving grudger with end-game defection."""

from axelrod.action import Action
from axelrod.player import Player

C, D = Action.C, Action.D


class Ioannis(Player):
    """Reciprocator with asymmetric grudge accounting and end-game defection.

    Each opponent defection adds 2 to a grudge counter; each cooperation
    subtracts 1 (floored at 0). We defect whenever the counter is at least 1
    — so a single defection triggers retaliation for two of our rounds
    (one to retaliate, one because the counter is still 1 after the first
    forgiveness), and any opponent must cooperate twice to undo each of
    their defections.

    Additionally, on the final 3 rounds of the match we always defect,
    grabbing free points against unconditional cooperators and tit-for-tat
    types where retaliation can no longer be punished by future rounds.
    """

    name = "WAS - Ioannis"
    classifier = {
        "memory_depth": float("inf"),
        "stochastic": False,
        "long_run_time": False,
        "inspects_source": False,
        "manipulates_source": False,
        "manipulates_state": False,
    }

    DEFECT_THRESHOLD = 1
    DEFECT_INCREMENT = 2
    FORGIVE_DECREMENT = 1
    END_GAME_DEFECT_ROUNDS = 3

    def __init__(self) -> None:
        super().__init__()
        self.grudge = 0

    def strategy(self, opponent: Player) -> Action:
        if not self.history:
            self.grudge = 0
            return C

        match_length = self.match_attributes.get("length", -1)
        if (
            match_length > 0
            and len(self.history) >= match_length - self.END_GAME_DEFECT_ROUNDS
        ):
            return D

        if opponent.history[-1] == D:
            self.grudge += self.DEFECT_INCREMENT
        else:
            self.grudge = max(0, self.grudge - self.FORGIVE_DECREMENT)

        return D if self.grudge >= self.DEFECT_THRESHOLD else C
