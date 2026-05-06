"""Auto-generated strategy loader for nemotron-3-super:cloud.

Compiles the JSON DSL document next to this file into an axelrod Player.
"""

from pathlib import Path

from wasstrategies._dsl import compile_from_file

_DOC_PATH = Path(__file__).with_suffix(".json")
Nemotron3Super = compile_from_file(str(_DOC_PATH))
Nemotron3Super.__module__ = __name__
