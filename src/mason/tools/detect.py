"""Shared executable discovery and subprocess helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

from mason.core.results import ExecutionResult

VERSION_TIMEOUT = 8


def which(name: str) -> Path | None:
    """Return the first PATH hit for name, or None."""
    found = shutil.which(name)
    return Path(found) if found else None


def first_existing(candidates: Iterable[Path]) -> Path | None:
    """Return the first existing file path."""
    for path in candidates:
        try:
            if path.is_file():
                return path.resolve()
        except OSError:
            continue
    return None


def glob_files(pattern_dirs: Iterable[Path], name: str) -> list[Path]:
    """Find name under each directory glob."""
    hits: list[Path] = []
    for directory in pattern_dirs:
        try:
            if not directory.parent.exists() and "*" not in str(directory):
                continue
            parent = directory.parent
            if "*" in directory.name:
                matches = sorted(parent.glob(directory.name), reverse=True)
            elif directory.is_dir():
                matches = [directory]
            else:
                continue
            for match in matches:
                candidate = match / name
                if candidate.is_file():
                    hits.append(candidate.resolve())
        except OSError:
            continue
    return hits


def run_version(executable: Path, args: list[str]) -> tuple[int, str]:
    """Run executable with args; return (exit_code, combined text)."""
    try:
        proc = subprocess.run(
            [str(executable), *args],
            capture_output=True,
            text=True,
            timeout=VERSION_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    text = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, text


def run_logged(
    command: list[str],
    stdout_path: Path,
    stderr_path: Path,
    *,
    cwd: Path | None = None,
    timeout: int = 600,
    env: dict[str, str] | None = None,
) -> ExecutionResult:
    """Run a command, write logs, return ExecutionResult."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            check=False,
            env=merged_env,
        )
        stdout_path.write_text(proc.stdout or "", encoding="utf-8")
        stderr_path.write_text(proc.stderr or "", encoding="utf-8")
        return ExecutionResult(
            command=command,
            exit_code=proc.returncode,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            success=proc.returncode == 0,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(exc.stdout or "" if isinstance(exc.stdout, str) else "", encoding="utf-8")
        stderr_path.write_text(
            f"Timed out after {timeout}s\n{exc.stderr or ''}",
            encoding="utf-8",
        )
        return ExecutionResult(
            command=command,
            exit_code=-1,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            success=False,
        )
    except OSError as exc:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(str(exc), encoding="utf-8")
        return ExecutionResult(
            command=command,
            exit_code=-1,
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
            success=False,
        )


def parse_version_token(text: str) -> str | None:
    """Pull the first dotted numeric version from text."""
    import re

    match = re.search(r"\b(\d+\.\d+(?:\.\d+)?)\b", text)
    return match.group(1) if match else None
