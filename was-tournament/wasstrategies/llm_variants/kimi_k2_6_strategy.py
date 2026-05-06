"""Auto-generated strategy loader for kimi-k2.6:cloud.

Compiles the JSON DSL document next to this file into an axelrod Player.
"""

from pathlib import Path

from wasstrategies._dsl import compile_from_file

_DOC_PATH = Path(__file__).with_suffix(".json")
KimiK26 = compile_from_file(str(_DOC_PATH))
KimiK26.__module__ = __name__
