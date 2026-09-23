"""Tier 1 Mode B reader using one ephemeral Codex CLI process per attempt.

Only the image paths assigned by the manifest are attached to a reader. The
operator never decodes them. No direct OpenAI API client or API key is used.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from control import OUTPUT, PACKAGE, ReadSpec, RunControl


RUNNER = Path(__file__).resolve().parent
MODEL = "gpt-6-astra"
TIMEOUT_SECONDS = 1800
DEVIATIONS = [
    "Mode B used because the local Windows image-view wrapper could not "
    "return PNGs to the reader in Mode A.",
    "Codex CLI does not expose a per-image detail setting; native PNG files "
    "are attached without resizing, with CLI-managed image detail.",
    "Codex CLI does not report the effective default reasoning effort or "
    "the API-returned model identifier; metadata records the requested "
    "model gpt-6-astra and an unspecified default effort.",
    "Codex CLI does not provide a switch that removes all agent tools; "
    "the runner rejects any read whose event stream reports a tool call.",
    "The user requested fresh Codex agents instead of the direct API runner "
    "specified in the operator instructions.",
    "Web tools are not separately exposed or invoked in this CLI setup, "
    "but the CLI does not provide an independently verified web-disable flag.",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reader_command(image_paths: list[Path], output_path: Path) -> list[str]:
    return [
        "codex", "exec", "--ephemeral", "--ignore-user-config",
        "--ignore-rules", "--skip-git-repo-check", "--sandbox", "read-only",
        "--model", MODEL, "--cd", str(image_paths[0].parent),
        "--output-schema", str(PACKAGE / "output_schema.json"),
        "--output-last-message", str(output_path), "--json", "--image",
        *(str(path) for path in image_paths),
    ]


def _events(stdout: str) -> tuple[dict[str, Any], bool, list[str]]:
    usage: dict[str, Any] = {}
    tools_used = False
    errors: list[str] = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type", "")
        if kind == "turn.completed":
            usage = event.get("usage") or {}
        if kind in {"turn.failed", "error"}:
            errors.append(str(event.get("error") or event.get("message") or kind))
        item = event.get("item") or {}
        if kind.startswith("item.") and item.get("type") not in {
            "agent_message", "reasoning", "user_message", None,
        }:
            tools_used = True
    return usage, tools_used, errors


def one_attempt(
    prompt: str, image_paths: list[Path], *, timeout: int = TIMEOUT_SECONDS,
) -> tuple[Any | None, dict[str, Any], str | None]:
    """Return parsed response, usage, error. Never writes to outputs/."""
    if not image_paths or len(set(image_paths)) != len(image_paths):
        raise ValueError("empty or repeated image list")
    parent = image_paths[0].parent
    if any(path.parent != parent or not path.is_file() or path.is_symlink()
           for path in image_paths):
        raise ValueError("images must be regular files in one assigned folder")
    with tempfile.TemporaryDirectory(prefix="cli_read_", dir=RUNNER) as temp:
        message_path = Path(temp) / "response.json"
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        # The bundled Windows CLI requires HOME even when USERPROFILE exists.
        if not env.get("HOME"):
            env["HOME"] = env["USERPROFILE"]
        if not env.get("CODEX_HOME"):
            env["CODEX_HOME"] = str(Path(env["USERPROFILE"]) / ".codex")
        command = _reader_command(image_paths, message_path)
        try:
            completed = subprocess.run(
                command, input=prompt, text=True, encoding="utf-8",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=parent,
                env=env, timeout=timeout, check=False,
            )
        except subprocess.TimeoutExpired:
            return None, {}, f"Codex CLI timed out after {timeout} seconds"
        except OSError as exc:
            return None, {}, f"Codex CLI launch failed: {exc}"
        usage, tools_used, event_errors = _events(completed.stdout)
        if tools_used:
            raise RuntimeError("Reader invoked a tool in Mode B; run stopped")
        if message_path.is_file():
            # A completed answer is never repeated even if CLI cleanup fails.
            response = message_path.read_text(encoding="utf-8")
            if not response.strip():
                return None, usage, "Codex CLI wrote an empty final message"
            if completed.returncode or event_errors:
                usage["_cli_warning"] = (
                    "; ".join(event_errors) or completed.stderr.strip()
                )[:500]
            try:
                return json.loads(response), usage, None
            except json.JSONDecodeError:
                return response, usage, None
        detail = "; ".join(event_errors) or completed.stderr.strip()
        return None, usage, f"Codex CLI exit {completed.returncode}: {detail[:1000]}"


def read_with_retries(spec: ReadSpec, control: RunControl) -> tuple[Any | None, dict[str, Any]]:
    """Retry transport at most twice, invalid output at most twice."""
    paths = [spec.image_dir / name for name in spec.files]
    transport_retries = invalid_retries = 0
    total_retries = 0
    last_usage: dict[str, Any] = {}
    notes: list[str] = []
    while True:
        result, usage, error = one_attempt(spec.prompt, paths)
        last_usage = usage
        if usage.get("_cli_warning"):
            notes.append(f"CLI completion warning: {usage['_cli_warning']}")
        if error is not None:
            notes.append(error)
            if transport_retries >= 2:
                raise RuntimeError(
                    f"Transport failed on 3 attempts for {spec.key}: {error}"
                )
            transport_retries += 1
            total_retries += 1
            continue
        try:
            control.check_result(result)
        except ValueError as exc:
            notes.append(f"Invalid output: {exc}; response={str(result)[:500]}")
            if invalid_retries >= 2:
                result = None
                break
            invalid_retries += 1
            total_retries += 1
            continue
        break
    meta = {
        "model": MODEL,
        "timestamp": now(),
        "harness": "B",
        "reasoning_effort": "default (not reported by Codex CLI)",
        "tool_calls": {"file_read": 0, "code": 0, "other": 0},
        "input_tokens": last_usage.get("input_tokens"),
        "output_tokens": last_usage.get("output_tokens"),
        "retries": total_retries,
        "notes": "; ".join(notes),
    }
    return result, meta


def _run_info(existing: dict[str, Any] | None, *, finished: bool) -> dict[str, Any]:
    info = dict(existing or {})
    cli_home = Path(
        os.environ.get("CODEX_HOME") or Path(os.environ["USERPROFILE"]) / ".codex"
    ).resolve()
    deviations = list(DEVIATIONS)
    if not cli_home.is_relative_to(PACKAGE.resolve()):
        deviations.append(
            "The authenticated Codex CLI used its own state and temporary "
            "files under CODEX_HOME outside the study package."
        )
    for deviation in deviations:
        if deviation not in info.get("deviations", []):
            info.setdefault("deviations", []).append(deviation)
    info.update({
        "provider": "OpenAI", "model": MODEL, "harness_mode": "B",
        "harness_description": "codex-cli 0.155.0-alpha.16; new ephemeral exec per attempt",
        "reasoning_effort": "default (not reported by Codex CLI)",
        "image_detail": "CLI-managed (not exposed)",
        "structured_output_method": "native_strict",
        "web_access": False, "tiers_run": [1],
    })
    info.setdefault("date_started", now())
    info["date_finished"] = now() if finished else None
    return info


def _save_info(info: dict[str, Any]) -> None:
    OUTPUT.mkdir(exist_ok=True)
    path = OUTPUT / "run_info.json"
    temporary = OUTPUT / "run_info.json.tmp"
    temporary.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_tier1() -> None:
    control = RunControl("B")
    existing = control.existing()
    info_path = OUTPUT / "run_info.json"
    prior_info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else None
    if prior_info and prior_info.get("harness_mode") not in (None, "B"):
        raise RuntimeError("existing run_info.json has a different harness mode")
    if any(row["meta"]["harness"] == "A" for row in existing):
        prior_info = dict(prior_info or {})
        historic = (
            "The first three S1 reads predate this Mode B CLI run, used a separate "
            "agentic harness, and have incomplete historical metadata. They were "
            "preserved without repetition."
        )
        if historic not in prior_info.get("deviations", []):
            prior_info.setdefault("deviations", []).append(historic)
    _save_info(_run_info(prior_info, finished=False))
    print(f"Tier 1: {len(existing)}/{len(control.plan)} already saved", flush=True)
    retries_total = 0
    failed_results = 0
    while (spec := control.next_read()) is not None:
        result, meta = read_with_retries(spec, control)
        control.append(spec, result, meta)
        retries_total += meta["retries"]
        failed_results += result is None
        done = len(control.existing())
        if done % 50 == 0 or done == len(control.plan):
            print(
                f"Saved {done}/{len(control.plan)} reads; "
                f"retries={retries_total}; null_results={failed_results}",
                flush=True,
            )
    _save_info(_run_info(json.loads(info_path.read_text(encoding="utf-8")), finished=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-tier1", action="store_true", help="start or resume clinical Tier 1")
    args = parser.parse_args()
    if not args.run_tier1:
        parser.error("explicit --run-tier1 is required; synthetic test is separate")
    run_tier1()


if __name__ == "__main__":
    main()
