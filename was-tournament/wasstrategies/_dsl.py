"""A tiny declarative DSL for Axelrod strategies.

A strategy is a JSON document. We validate it against a fixed schema and then
compile it into an `axelrod.player.Player` subclass at import time. This lets
the cloud LLMs return data instead of free-form Python: no imports, no loops,
no surprise side effects.

Document shape (informal):

    {
      "name": "ForgivingTFT",
      "description": "...",
      "first_moves": ["C"],            # actions for the opening rounds
      "rules": [                       # ordered, first match wins
        {"when": {"opponent_last": "D",
                  "consecutive_opponent_defects": {">=": 2}},
         "action": "D"},
        {"when": {"opponent_defection_rate": {"<": 0.3}},
         "action": "C"}
      ],
      "default": "C"                   # fallback action; required
    }

Features available inside `when`:
  - opponent_last:                    "C" | "D"
  - my_last:                          "C" | "D"
  - round:                            int (0-indexed turn number)
  - total_turns:                      int (match length, may be None)
  - opponent_defections:              int
  - opponent_cooperations:            int
  - opponent_defection_rate:          float in [0,1]
  - consecutive_opponent_defects:     int (current streak)
  - consecutive_opponent_cooperates:  int

A `when` clause is one of:
  - {} (always true)
  - {"feature": "C"}                  -> equality
  - {"feature": {"==": v}}            -> equality (any of ==, !=, <, <=, >, >=, in)
  - {"all": [clause, clause, ...]}    -> AND
  - {"any": [clause, clause, ...]}    -> OR
  - {"not": clause}                   -> negation

Action is one of:
  - "C" | "D"
  - {"random_defect": p}              -> defect with probability p, else C
"""

from __future__ import annotations

import json
from typing import Any

from axelrod.action import Action
from axelrod.player import Player

C, D = Action.C, Action.D
_ACTION_MAP = {"C": C, "D": D}

ALLOWED_FEATURES = {
    "opponent_last",
    "my_last",
    "round",
    "total_turns",
    "opponent_defections",
    "opponent_cooperations",
    "opponent_defection_rate",
    "consecutive_opponent_defects",
    "consecutive_opponent_cooperates",
}
COMPARISON_OPS = {"==", "!=", "<", "<=", ">", ">="}


class DSLError(ValueError):
    """Raised when a DSL document fails validation."""


def _validate_action(action: Any, where: str) -> None:
    if action in ("C", "D"):
        return
    if isinstance(action, dict) and set(action.keys()) == {"random_defect"}:
        p = action["random_defect"]
        if not isinstance(p, (int, float)) or not 0.0 <= float(p) <= 1.0:
            raise DSLError(f"{where}: random_defect probability must be in [0,1]")
        return
    raise DSLError(f"{where}: action must be 'C', 'D', or {{'random_defect': p}}; got {action!r}")


def _validate_clause(clause: Any, where: str) -> None:
    if not isinstance(clause, dict):
        raise DSLError(f"{where}: 'when' clause must be an object")
    if not clause:
        return
    if set(clause.keys()) == {"all"} or set(clause.keys()) == {"any"}:
        items = next(iter(clause.values()))
        if not isinstance(items, list) or not items:
            raise DSLError(f"{where}: '{next(iter(clause))}' must be a non-empty list")
        for i, item in enumerate(items):
            _validate_clause(item, f"{where}[{i}]")
        return
    if set(clause.keys()) == {"not"}:
        _validate_clause(clause["not"], f"{where}.not")
        return
    for key, val in clause.items():
        if key in {"all", "any", "not"}:
            raise DSLError(
                f"{where}: '{key}' is a composite operator and must be the only key"
                f" in its clause; combine with siblings by nesting"
                f" (e.g. {{'all': [{{'all': [...]}}, {{'any': [...]}}]}})"
            )
        if key not in ALLOWED_FEATURES:
            raise DSLError(
                f"{where}: unknown feature '{key}'. Allowed: {sorted(ALLOWED_FEATURES)}"
            )
        if isinstance(val, dict):
            for op in val:
                if op not in COMPARISON_OPS and op != "in":
                    raise DSLError(
                        f"{where}.{key}: unknown operator '{op}'."
                        f" Allowed: {sorted(COMPARISON_OPS | {'in'})}"
                    )
            if "in" in val and not isinstance(val["in"], list):
                raise DSLError(f"{where}.{key}.in: must be a list")


def validate(doc: dict) -> None:
    """Raise DSLError if the document is malformed. No return value on success."""
    if not isinstance(doc, dict):
        raise DSLError("strategy must be a JSON object")
    name = doc.get("name")
    if not isinstance(name, str) or not name.isidentifier():
        raise DSLError("'name' must be a valid Python identifier string")
    if "description" in doc and not isinstance(doc["description"], str):
        raise DSLError("'description' must be a string if present")

    first_moves = doc.get("first_moves", [])
    if not isinstance(first_moves, list) or not all(m in ("C", "D") for m in first_moves):
        raise DSLError("'first_moves' must be a list of 'C'/'D' strings")

    rules = doc.get("rules", [])
    if not isinstance(rules, list):
        raise DSLError("'rules' must be a list")
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict) or set(rule.keys()) - {"when", "action"}:
            raise DSLError(f"rule[{i}]: must be an object with 'when' and 'action'")
        _validate_clause(rule.get("when", {}), f"rule[{i}].when")
        _validate_action(rule.get("action"), f"rule[{i}].action")

    if "default" not in doc:
        raise DSLError("'default' action is required")
    _validate_action(doc["default"], "default")


def _extract_features(player: Player, opponent: Player) -> dict[str, Any]:
    opp_history = list(opponent.history)
    my_history = list(player.history)
    n_def = sum(1 for a in opp_history if a == D)
    n_coop = len(opp_history) - n_def
    streak_d = streak_c = 0
    for a in reversed(opp_history):
        if a == D and streak_c == 0:
            streak_d += 1
        elif a == C and streak_d == 0:
            streak_c += 1
        else:
            break
    return {
        "opponent_last": "D" if opp_history and opp_history[-1] == D
                          else "C" if opp_history else None,
        "my_last": "D" if my_history and my_history[-1] == D
                    else "C" if my_history else None,
        "round": len(my_history),
        "total_turns": getattr(player, "match_attributes", {}).get("length"),
        "opponent_defections": n_def,
        "opponent_cooperations": n_coop,
        "opponent_defection_rate": (n_def / len(opp_history)) if opp_history else 0.0,
        "consecutive_opponent_defects": streak_d,
        "consecutive_opponent_cooperates": streak_c,
    }


def _eval_clause(clause: dict, feats: dict[str, Any]) -> bool:
    if not clause:
        return True
    if "all" in clause:
        return all(_eval_clause(c, feats) for c in clause["all"])
    if "any" in clause:
        return any(_eval_clause(c, feats) for c in clause["any"])
    if "not" in clause:
        return not _eval_clause(clause["not"], feats)
    for feat, expected in clause.items():
        actual = feats.get(feat)
        if isinstance(expected, dict):
            for op, target in expected.items():
                if not _compare(actual, op, target):
                    return False
        else:
            if actual != expected:
                return False
    return True


def _compare(actual: Any, op: str, target: Any) -> bool:
    if actual is None:
        return False
    if op == "in":
        return actual in target
    if op == "==":
        return actual == target
    if op == "!=":
        return actual != target
    if op == "<":
        return actual < target
    if op == "<=":
        return actual <= target
    if op == ">":
        return actual > target
    if op == ">=":
        return actual >= target
    raise DSLError(f"unknown operator {op}")


def _resolve_action(action: Any, player: Player) -> Action:
    if isinstance(action, str):
        return _ACTION_MAP[action]
    p = float(action["random_defect"])
    return D if player._random.random() < p else C


def compile_dsl(doc: dict) -> type[Player]:
    """Validate `doc` and return a fresh `Player` subclass that implements it."""
    validate(doc)
    cls_name = doc["name"]
    description = doc.get("description", "DSL-defined strategy.")
    first_moves = [_ACTION_MAP[m] for m in doc.get("first_moves", [])]
    rules = doc.get("rules", [])
    default_action = doc["default"]
    is_stochastic = (
        isinstance(default_action, dict)
        or any(isinstance(r["action"], dict) for r in rules)
    )

    def strategy(self: Player, opponent: Player) -> Action:  # noqa: D401
        idx = len(self.history)
        if idx < len(first_moves):
            return first_moves[idx]
        feats = _extract_features(self, opponent)
        for rule in rules:
            if _eval_clause(rule.get("when", {}), feats):
                return _resolve_action(rule["action"], self)
        return _resolve_action(default_action, self)

    cls = type(
        cls_name,
        (Player,),
        {
            "__doc__": description,
            "name": cls_name,
            "classifier": {
                "memory_depth": float("inf"),
                "stochastic": is_stochastic,
                "inspects_source": False,
                "manipulates_source": False,
                "manipulates_state": False,
            },
            "strategy": strategy,
        },
    )
    return cls


def compile_from_file(path: str) -> type[Player]:
    with open(path) as f:
        return compile_dsl(json.load(f))


SCHEMA_PROMPT = """STRATEGY DSL — return ONLY a JSON object with this shape:

{
  "name": "<PythonIdentifier>",       // class name, e.g. "DeepseekV4Flash"
  "description": "<one-line summary of the game-theoretic reasoning>",
  "first_moves": ["C"],                // 0+ opening moves, e.g. ["C"] or ["C","C"]
  "rules": [                            // ordered; first matching rule fires
    {"when": <clause>, "action": <action>},
    ...
  ],
  "default": <action>                   // required; used when no rule matches
}

ACTIONS:
  "C" | "D" | {"random_defect": <p in [0,1]>}

FEATURES usable in <clause> (read-only signals about the match so far):
  opponent_last, my_last:               "C" or "D" (null on round 0 — handle via first_moves)
  round:                                int, 0-indexed turn number
  total_turns:                          int or null, match length
  opponent_defections, opponent_cooperations: int
  opponent_defection_rate:              float in [0,1]
  consecutive_opponent_defects:         int, current D-streak length
  consecutive_opponent_cooperates:      int, current C-streak length

CLAUSE forms (compose freely):
  {}                                          // always true
  {"feature": "C"}                            // equality shorthand
  {"feature": {"==": v}}                      // also: !=, <, <=, >, >=
  {"feature": {"in": [v1, v2, ...]}}
  {"all": [<clause>, <clause>, ...]}          // AND
  {"any": [<clause>, <clause>, ...]}          // OR
  {"not": <clause>}                           // negation

  IMPORTANT: "all" / "any" / "not" must each be the ONLY key in their object.
  To mix them, NEST them. Wrong: {"all":[A,B], "any":[C,D]}.
  Right:       {"all":[A, B, {"any":[C,D]}]}.

EXAMPLES:

TitForTat:
{"name": "TFT", "description": "copy opponent's last move",
 "first_moves": ["C"], "rules": [], "default": "C"}

Grudger:
{"name": "Grudger", "description": "C until first D, then D forever",
 "first_moves": ["C"],
 "rules": [{"when": {"opponent_defections": {">": 0}}, "action": "D"}],
 "default": "C"}

Generous TFT:
{"name": "GTFT", "description": "TFT but forgive 20% of defections",
 "first_moves": ["C"],
 "rules": [{"when": {"opponent_last": "D"}, "action": {"random_defect": 0.8}}],
 "default": "C"}

End-game defector:
{"name": "Endgamer", "description": "TFT, but defect in the last 2 rounds",
 "first_moves": ["C"],
 "rules": [
   {"when": {"all": [{"total_turns": {"!=": null}},
                     {"round": {">=": 8}}]}, "action": "D"},
   {"when": {"opponent_last": "D"}, "action": "D"}
 ],
 "default": "C"}

HARD RULES:
- Output MUST be a single JSON object — no markdown, no prose, no comments.
- "name" must be a valid Python identifier (letters/digits/underscore, no leading digit).
- Do not invent features or operators outside the lists above.
- Keep the strategy short and game-theoretically motivated.
"""
