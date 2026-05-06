"""Auto-generated strategy loader for deepseek-v4-flash:cloud.

Compiles the JSON DSL document next to this file into an axelrod Player.
"""

from pathlib import Path

from wasstrategies._dsl import compile_from_file

_DOC_PATH = Path(__file__).with_suffix(".json")
DeepseekV4Flash = compile_from_file(str(_DOC_PATH))
DeepseekV4Flash.__module__ = __name__
