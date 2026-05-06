"""Auto-generated strategy loader for qwen3.5:cloud.

Compiles the JSON DSL document next to this file into an axelrod Player.
"""

from pathlib import Path

from wasstrategies._dsl import compile_from_file

_DOC_PATH = Path(__file__).with_suffix(".json")
Qwen35 = compile_from_file(str(_DOC_PATH))
Qwen35.__module__ = __name__
