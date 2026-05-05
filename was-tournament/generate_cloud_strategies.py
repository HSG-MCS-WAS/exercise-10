"""Ask each Ollama :cloud model to author an Axelrod strategy and validate it.

For every cloud-hosted model exposed by the local Ollama server we:
  1. prompt the model for a JSON strategy document conforming to wasstrategies._dsl,
  2. write the JSON to `wasstrategies/<model_slug>_strategy.json`,
  3. emit a thin `<model_slug>_strategy.py` that compiles the JSON at import,
  4. validate that it compiles and plays a short smoke-test match,
  5. on success, append both files to `.gitignore`; otherwise delete them.
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import axelrod as axl
import ollama

OLLAMA_HOST = "http://localhost:11434"
_client = ollama.Client(host=OLLAMA_HOST)
REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGIES_DIR = Path(__file__).resolve().parent / "wasstrategies"
GITIGNORE = REPO_ROOT / ".gitignore"

# Per-model retry budget when the *response* is bad (no JSON, parse error, DSL
# error, smoke-test crash). Transport errors from Ollama are not retried — those
# usually mean the local server is unreachable.
MAX_ATTEMPTS = 3

# Make the DSL importable when this script is run directly.
sys.path.insert(0, str(STRATEGIES_DIR.parent))
from wasstrategies._dsl import DSLError, SCHEMA_PROMPT, compile_dsl  # noqa: E402


def log(msg: str) -> None:
    """Timestamped, line-flushed log so progress is visible during long calls."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

PROMPT_TEMPLATE = """You are designing a strategy for the Axelrod Iterated Prisoner's Dilemma tournament.

THINK SMART. THINK LIKE A GAME THEORIST.

PRIMER — who you are up against:
You are not the only LLM in this tournament. We run this exact prompt against
EVERY :cloud model the local Ollama instance exposes (currently
deepseek-v4-flash, minimax-m2, and any other :cloud model that gets added).
Each model produces one strategy. All of those LLM-authored strategies, plus
the classic baselines (TitForTat, Grudger, Defector, Cooperator, Random(0.5))
plus several human student strategies, will all play a 10-turn round-robin
against each other and against you. Your opponents therefore include:
  * other LLMs that just received this same primer and are also "trying to be
    smart" — expect them to lean nice-but-retaliatory and to over-think;
  * the canonical zoo (always-C, always-D, TFT, Grudger, Random);
  * unknown student strategies that may be naive, vindictive, or weird.
Design for that mixed field. A strategy that beats TitForTat 1-on-1 but loses
to Defector and to its own clone will lose the tournament.

Tournament rules: 10-turn matches, round-robin. Payoffs (lower is worse —
years in prison): (C,C)=-1, (C,D)=-5, (D,C)=0, (D,D)=-3. Goal: minimise total
prison time across the round-robin.

Reason about: the shadow of the future, niceness vs provocability, forgiveness,
exploitation of unconditional cooperators, retaliation, end-game effects in a
fixed 10-turn horizon, and how your strategy performs against its own clone.
Axelrod's classic finding: nice + retaliatory + forgiving + clear wins.

You will NOT write Python. You will return a single JSON object that conforms
to the strategy DSL below. The runner compiles it into a Player at load time.
The "name" field MUST be exactly "{class_name}".

{schema}
"""


RETRY_SUFFIX = """

----
RETRY (attempt {attempt} of {max_attempts}). Your previous response was rejected:

  reason: {reason}

  previous response (truncated):
  {prev_snippet}

Read the schema above carefully and produce a corrected single JSON object.
Do not repeat the same mistake. Output ONLY the JSON object, no prose.
"""


def list_cloud_models() -> list[str]:
    log(f"ollama.list() @ {OLLAMA_HOST}")
    t0 = time.monotonic()
    models = _client.list().models
    log(f"  -> {len(models)} total models ({time.monotonic()-t0:.2f}s)")
    return [m.model for m in models if ":cloud" in m.model]


def ask_model(model: str, prompt: str) -> tuple[str, str]:
    """Stream a generation from Ollama, returning (response_text, thinking_text)."""
    log(f"  ollama.generate model={model} prompt_chars={len(prompt)} (streaming)")
    t0 = time.monotonic()
    response_buf: list[str] = []
    thinking_buf: list[str] = []
    last_tick = t0
    last_dump_resp = 0
    last_dump_think = 0
    final: ollama.GenerateResponse | None = None

    for chunk in _client.generate(model=model, prompt=prompt, stream=True):
        if chunk.response:
            response_buf.append(chunk.response)
        if chunk.thinking:
            thinking_buf.append(chunk.thinking)

        now = time.monotonic()
        if now - last_tick >= 5.0:
            r = sum(len(s) for s in response_buf)
            t = sum(len(s) for s in thinking_buf)
            phase = "thinking" if r == 0 and t > 0 else "answering"
            log(f"    ... {phase}: think={t} resp={r} ({now - t0:.1f}s elapsed)")
            if r > last_dump_resp:
                log(f"      RESP+: {''.join(response_buf)[last_dump_resp:][:400]!r}")
                last_dump_resp = r
            if t > last_dump_think:
                log(f"      THINK+: {''.join(thinking_buf)[last_dump_think:][:400]!r}")
                last_dump_think = t
            last_tick = now

        if chunk.done:
            final = chunk
            break

    elapsed = time.monotonic() - t0
    response_text = "".join(response_buf)
    thinking_text = "".join(thinking_buf)
    done_reason = final.done_reason if final else None
    log(
        f"  <- response={len(response_text)} chars,"
        f" thinking={len(thinking_text)} chars, {elapsed:.1f}s,"
        f" done_reason={done_reason}"
    )

    if not response_text and thinking_text:
        log("  NOTE: response was empty; falling back to 'thinking' content")
        return thinking_text, thinking_text
    return response_text, thinking_text


def save_thinking(
    path: Path,
    model: str,
    thinking_text: str,
    response_text: str,
    outcome: str,
) -> None:
    """Persist the model's reasoning trace next to its strategy file."""
    if not thinking_text and not response_text:
        return
    header = (
        f"# model: {model}\n"
        f"# generated: {datetime.now().isoformat(timespec='seconds')}\n"
        f"# outcome: {outcome}\n"
        f"# response_chars: {len(response_text)}\n"
        f"# thinking_chars: {len(thinking_text)}\n"
        "\n"
        "===== THINKING =====\n"
    )
    body = thinking_text or "(no thinking trace returned)\n"
    tail = "\n===== RESPONSE =====\n" + (response_text or "(empty)\n")
    path.write_text(header + body + tail)
    log(f"  saved thinking trace -> {path.name} ({len(thinking_text)} chars)")


def slugify_model(model: str) -> tuple[str, str]:
    """Return (file_slug, ClassName) derived from an Ollama model name."""
    base = model.split(":", 1)[0]
    slug = re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_") or "model"
    parts = re.split(r"[^a-zA-Z0-9]+", base)
    class_name = "".join(p.capitalize() for p in parts if p) or "CloudModel"
    if not class_name[0].isalpha():
        class_name = "M" + class_name
    return slug, class_name


def strip_fences(text: str) -> str:
    """Remove ```python|json ... ``` fences if the model wrapped its output."""
    text = text.strip()
    fence = re.match(r"^```(?:python|json)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    return text


def extract_json_object(text: str) -> str | None:
    """Pull the first balanced top-level JSON object out of a noisy response."""
    text = strip_fences(text)
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


LOADER_TEMPLATE = '''"""Auto-generated strategy loader for {model}.

Compiles the JSON DSL document next to this file into an axelrod Player.
"""

from pathlib import Path

from wasstrategies._dsl import compile_from_file

_DOC_PATH = Path(__file__).with_suffix(".json")
{class_name} = compile_from_file(str(_DOC_PATH))
{class_name}.__module__ = __name__
'''


def ensure_gitignored(rel_path: str) -> None:
    existing = GITIGNORE.read_text().splitlines() if GITIGNORE.exists() else []
    if rel_path in existing:
        return
    with GITIGNORE.open("a") as f:
        if existing and existing[-1] != "":
            f.write("\n")
        f.write(rel_path + "\n")
    print(f"    added to .gitignore: {rel_path}")


def main() -> int:
    overall_t0 = time.monotonic()
    STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    models = list_cloud_models()
    if not models:
        log("No :cloud models found in Ollama tags.")
        return 1
    log(f"Found {len(models)} cloud model(s): {', '.join(models)}")

    successes: list[str] = []
    failures: list[tuple[str, str]] = []

    for idx, model in enumerate(models, start=1):
        slug, class_name = slugify_model(model)
        json_path = STRATEGIES_DIR / f"{slug}_strategy.json"
        py_path = STRATEGIES_DIR / f"{slug}_strategy.py"
        thinking_path = STRATEGIES_DIR / f"{slug}_strategy.thinking.txt"
        log(f"[{idx}/{len(models)}] {model} -> {py_path.name} + {json_path.name}")

        if json_path.exists() and py_path.exists():
            log(f"  SKIP: {json_path.name} already exists")
            continue

        base_prompt = PROMPT_TEMPLATE.format(
            class_name=class_name,
            schema=SCHEMA_PROMPT,
        )

        last_reason: str | None = None
        last_raw = ""
        last_thinking = ""
        last_snippet = ""
        accepted_doc: dict | None = None
        transport_error: str | None = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            if attempt == 1:
                prompt = base_prompt
            else:
                log(f"  retry {attempt}/{MAX_ATTEMPTS} after: {last_reason}")
                prompt = base_prompt + RETRY_SUFFIX.format(
                    attempt=attempt,
                    max_attempts=MAX_ATTEMPTS,
                    reason=last_reason,
                    prev_snippet=last_snippet,
                )

            try:
                raw, thinking = ask_model(model, prompt)
            except Exception as exc:  # noqa: BLE001
                # Transport-level failures aren't retried — local server probably down.
                transport_error = f"ollama call failed: {exc!r}"
                log(f"  ERROR calling Ollama: {exc!r}")
                break

            last_raw = raw
            last_thinking = thinking
            last_snippet = (raw or "").strip()[:400]

            json_text = extract_json_object(raw)
            if json_text is None:
                last_reason = "no JSON object in response"
                log(f"  attempt {attempt}: {last_reason} (head: {raw[:120]!r})")
                continue
            try:
                doc = json.loads(json_text)
            except json.JSONDecodeError as exc:
                last_reason = f"json parse: {exc}"
                log(f"  attempt {attempt}: {last_reason}")
                continue

            if doc.get("name") != class_name:
                log(f"  note: model returned name={doc.get('name')!r}, rewriting to {class_name!r}")
                doc["name"] = class_name

            try:
                cls = compile_dsl(doc)
            except DSLError as exc:
                last_reason = f"dsl error: {exc}"
                log(f"  attempt {attempt}: INVALID DSL: {exc}")
                continue

            try:
                axl.Match((cls(), axl.Cooperator()), turns=5).play()
                axl.Match((cls(), axl.Defector()), turns=5).play()
            except Exception as exc:  # noqa: BLE001
                last_reason = f"runtime: {exc!r}"
                log(f"  attempt {attempt}: smoke-test crashed: {exc!r}")
                continue

            accepted_doc = doc
            last_reason = None
            break

        if transport_error is not None:
            failures.append((model, transport_error))
            continue

        if accepted_doc is None:
            save_thinking(thinking_path, model, last_thinking, last_raw, last_reason or "unknown")
            log(f"  GAVE UP after {MAX_ATTEMPTS} attempts: {last_reason}")
            failures.append((model, f"after {MAX_ATTEMPTS} attempts: {last_reason}"))
            continue

        json_path.write_text(json.dumps(accepted_doc, indent=2) + "\n")
        py_path.write_text(LOADER_TEMPLATE.format(model=model, class_name=class_name))
        save_thinking(thinking_path, model, last_thinking, last_raw, "ok")
        log(f"  OK: wrote {json_path.name} ({len(json.dumps(accepted_doc))} chars) and loader")
        for p in (json_path, py_path, thinking_path):
            ensure_gitignored(p.relative_to(REPO_ROOT).as_posix())
        successes.append(model)

    log(f"--- summary (total {time.monotonic()-overall_t0:.1f}s) ---")
    log(f"  succeeded: {len(successes)} ({', '.join(successes) or '-'})")
    log(f"  failed:    {len(failures)}")
    for m, why in failures:
        log(f"    - {m}: {why}")
    return 0 if successes else 2


if __name__ == "__main__":
    raise SystemExit(main())
