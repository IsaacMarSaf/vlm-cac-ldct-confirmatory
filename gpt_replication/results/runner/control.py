"""Deterministic Tier 1 plan and append-only output control.

This module reads only package metadata and image file headers. It never
interprets image pixels or changes a model's clinical answer.
"""

from __future__ import annotations

import json
import os
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


PACKAGE = Path(__file__).resolve().parent.parent
OUTPUT = PACKAGE / "outputs"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PLACEHOLDER = re.compile(r"\{(?:STUDY_DIR|N|LAST|FILE_LIST)\}")
PRIOR_CHAT_READS = (("S1", "C058", 1), ("S1", "C039", 1), ("S1", "C060", 1))


@dataclass(frozen=True)
class ReadSpec:
    set_id: str
    study_id: str
    read: int
    image_dir: Path
    files: tuple[str, ...]
    prompt: str

    @property
    def key(self) -> tuple[str, str, int]:
        return self.set_id, self.study_id, self.read


class RunControl:
    def __init__(self, mode: str = "A") -> None:
        if mode not in ("A", "B"):
            raise ValueError("mode must be A or B")
        self.mode = mode
        self.manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
        self.schema = json.loads((PACKAGE / "output_schema.json").read_text(encoding="utf-8"))
        self.plan = tuple(self._plan())
        if len({spec.key for spec in self.plan}) != len(self.plan):
            raise ValueError("duplicate read key in manifest")

    def _plan(self) -> Iterator[ReadSpec]:
        for group in self.manifest["sets"]:
            if group["tier"] != 1:
                continue
            template_path = PACKAGE / "prompts" / f"{group['prompt']}_MODE_{self.mode}.txt"
            template = template_path.read_text(encoding="utf-8")
            for read in range(1, group["reads_per_study"] + 1):
                for study in group["studies"]:
                    study_id = study["study_id"]
                    image_dir = (PACKAGE / group["image_root"] / study_id).resolve(strict=True)
                    if not image_dir.is_relative_to(PACKAGE / "images"):
                        raise ValueError(f"image directory escapes package: {study_id}")
                    count = study["n_slices"]
                    files = tuple(study.get("files") or (f"slice_{i:03d}.png" for i in range(count)))
                    if len(files) != count or len(set(files)) != count:
                        raise ValueError(f"invalid image list: {group['set']}/{study_id}")
                    for name in files:
                        if Path(name).name != name or not re.fullmatch(r"slice_\d{3}\.png", name):
                            raise ValueError(f"unsafe image name: {name}")
                        path = image_dir / name
                        if not path.is_file() or path.is_symlink():
                            raise ValueError(f"missing or linked image: {path}")
                    substitutions = {
                        "{STUDY_DIR}": str(image_dir) + os.sep,
                        "{N}": str(count),
                        "{LAST}": f"{count - 1:03d}",
                        "{FILE_LIST}": ", ".join(files),
                    }
                    prompt = PLACEHOLDER.sub(lambda match: substitutions[match.group()], template)
                    if PLACEHOLDER.search(prompt):
                        raise ValueError("unsubstituted prompt placeholder")
                    yield ReadSpec(group["set"], study_id, read, image_dir, files, prompt)

    def preflight(self) -> dict[str, int]:
        """Verify planned PNGs by header, without decoding their pixels."""
        checked: set[Path] = set()
        counts: dict[str, int] = {}
        for spec in self.plan:
            counts[spec.set_id] = counts.get(spec.set_id, 0) + 1
            for name in spec.files:
                path = spec.image_dir / name
                if path in checked:
                    continue
                checked.add(path)
                with path.open("rb") as stream:
                    head = stream.read(26)
                if len(head) != 26 or head[:8] != PNG_SIGNATURE or head[12:16] != b"IHDR":
                    raise ValueError(f"invalid PNG header: {path}")
                width, height, depth, color = struct.unpack(">IIBB", head[16:26])
                if (width, height, depth, color) != (512, 512, 8, 0):
                    raise ValueError(f"unexpected PNG format: {path}")
        return counts

    def check_result(self, result: Any) -> None:
        if not isinstance(result, dict):
            raise ValueError("result is not a JSON object")
        properties = self.schema["properties"]
        if set(result) != set(properties):
            raise ValueError("result fields differ from output_schema.json")
        for name, rule in properties.items():
            value = result[name]
            kind = rule["type"]
            good = {
                "boolean": lambda x: type(x) is bool,
                "integer": lambda x: type(x) is int,
                "string": lambda x: type(x) is str,
                "array": lambda x: isinstance(x, list) and all(type(y) is str for y in x),
            }[kind](value)
            if not good or ("enum" in rule and value not in rule["enum"]):
                raise ValueError(f"invalid result field: {name}")

    def existing(self) -> list[dict[str, Any]]:
        path = OUTPUT / "gpt_reads.jsonl"
        if not path.exists():
            return []
        rows = []
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                raise ValueError(f"blank output line {number}")
            row = json.loads(line)
            key = row.get("set"), row.get("study_id"), row.get("read")
            if number > len(self.plan) or key != self.plan[number - 1].key:
                raise ValueError(f"output order or key differs at line {number}")
            if row.get("result") is not None:
                self.check_result(row["result"])
            meta = row.get("meta")
            expected_harness = "A" if number <= len(PRIOR_CHAT_READS) and key == PRIOR_CHAT_READS[number - 1] else self.mode
            if not isinstance(meta, dict) or meta.get("harness") != expected_harness:
                raise ValueError(f"invalid metadata at line {number}")
            rows.append(row)
        return rows

    def next_read(self) -> ReadSpec | None:
        done = len(self.existing())
        return self.plan[done] if done < len(self.plan) else None

    def append(self, spec: ReadSpec, result: dict[str, Any] | None, meta: dict[str, Any]) -> None:
        done = len(self.existing())
        if done >= len(self.plan) or spec.key != self.plan[done].key:
            raise ValueError("read was already saved or is out of order")
        if result is not None:
            self.check_result(result)
        required = {
            "model", "timestamp", "harness", "reasoning_effort", "tool_calls",
            "input_tokens", "output_tokens", "retries", "notes",
        }
        if not isinstance(meta, dict) or not required.issubset(meta) or meta["harness"] != self.mode:
            raise ValueError("incomplete read metadata")
        row = {"set": spec.set_id, "study_id": spec.study_id, "read": spec.read,
               "result": result, "meta": meta}
        OUTPUT.mkdir(exist_ok=True)
        with (OUTPUT / "gpt_reads.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
