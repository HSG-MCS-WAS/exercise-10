"""Auto-generated strategy loader for qwen3-coder-next:cloud.

Compiles the JSON DSL document next to this file into an axelrod Player.
"""

from pathlib import Path

from wasstrategies._dsl import compile_from_file

_DOC_PATH = Path(__file__).with_suffix(".json")
Qwen3CoderNext = compile_from_file(str(_DOC_PATH))
Qwen3CoderNext.__module__ = __name__
