"""Typer CLI for Mason."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from mason import __version__
from mason.cli_render import (
    print_build,
    print_doctor,
    print_init,
    print_inspect,
    print_list,
)
from mason.core.config import (
    get_dotted,
    load_machine_config,
    save_machine_config,
    set_dotted,
)
from mason.core.jobs import list_jobs, require_job
from mason.core.workspace import find_project_root, init_project
from mason.errors import MasonError
from mason.pipelines.dispatch import run_build, run_rebuild
from mason.tools.registry import detect_all, doctor_payload, scan_and_store

app = typer.Typer(
    name="mason",
    no_args_is_help=True,
    add_completion=False,
    help="Asset-generation harness for coding agents.",
)
tools_app = typer.Typer(no_args_is_help=True, help="Tool discovery.")
config_app = typer.Typer(no_args_is_help=True, help="Machine config.")
app.add_typer(tools_app, name="tools")
app.add_typer(config_app, name="config")

JsonFlag = Annotated[
    bool,
    typer.Option("--json", help="Write JSON only to stdout."),
]


def _emit(json_mode: bool, data: dict[str, Any], render) -> None:
    if json_mode:
        typer.echo(json.dumps(data, indent=2))
    else:
        render()


def _fail(json_mode: bool, exc: MasonError) -> None:
    if json_mode:
        typer.echo(json.dumps(exc.to_dict(), indent=2))
    else:
        typer.secho(exc.message, err=True, fg=typer.colors.RED)
        if exc.hint:
            typer.secho(exc.hint, err=True)
    raise typer.Exit(code=1)


def _guard(json_mode: bool, fn):
    try:
        return fn()
    except MasonError as exc:
        _fail(json_mode, exc)


@app.command()
def version() -> None:
    """Print the Mason version."""
    typer.echo(__version__)


@app.command()
def doctor(json_mode: JsonFlag = False) -> None:
    """Detect installed creative tools and capabilities."""
    tools = detect_all()
    payload = doctor_payload(tools)
    _emit(json_mode, payload, lambda: print_doctor(tools))


@app.command()
def init(
    path: Annotated[Path, typer.Argument(dir_okay=True)] = Path("."),
    json_mode: JsonFlag = False,
) -> None:
    """Create mason.yaml, .mason/, and styles/default.yaml."""
    created = init_project(path)
    _emit(
        json_mode,
        {"success": True, "created": created},
        lambda: print_init(created),
    )


@app.command()
def build(
    spec: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    json_mode: JsonFlag = False,
) -> None:
    """Build an asset from a YAML spec."""

    def _run():
        result = run_build(spec)
        _emit(json_mode, result.model_dump(), lambda: print_build(result))
        if not result.success:
            raise typer.Exit(code=1)

    _guard(json_mode, _run)


@app.command()
def rebuild(
    asset_id: Annotated[str, typer.Argument()],
    json_mode: JsonFlag = False,
) -> None:
    """Rebuild a stored job by asset id."""

    def _run():
        result = run_rebuild(asset_id)
        _emit(json_mode, result.model_dump(), lambda: print_build(result))
        if not result.success:
            raise typer.Exit(code=1)

    _guard(json_mode, _run)


@app.command()
def preview(
    asset_id: Annotated[str, typer.Argument()],
    json_mode: JsonFlag = False,
) -> None:
    """Re-render previews for an existing job."""

    def _run():
        result = run_rebuild(asset_id, mode="preview")
        _emit(json_mode, result.model_dump(), lambda: print_build(result))
        if not result.success:
            raise typer.Exit(code=1)

    _guard(json_mode, _run)


@app.command()
def inspect(
    asset_id: Annotated[str, typer.Argument()],
    json_mode: JsonFlag = False,
) -> None:
    """Show stored job state for an asset."""

    def _run():
        root = find_project_root()
        job = require_job(root, asset_id)
        spec = job.load_spec()
        result = job.load_result()
        report = job.load_validation()
        payload = {
            "asset_id": spec.id,
            "name": spec.name,
            "type": spec.type,
            "style": spec.style,
            "source_spec": job.load_meta().source_spec if job.load_meta() else None,
            "tool": result.tool if result else None,
            "tool_version": result.tool_version if result else None,
            "outputs": result.outputs if result else {},
            "previews": result.previews if result else {},
            "validation": report.model_dump() if report else None,
            "built_at": result.built_at if result else None,
            "spec": spec.model_dump(mode="json"),
        }
        _emit(json_mode, payload, lambda: print_inspect(job, result))

    _guard(json_mode, _run)


@app.command()
def validate(
    asset_id: Annotated[str, typer.Argument()],
    json_mode: JsonFlag = False,
) -> None:
    """Re-run validation on stored outputs (no rebuild)."""

    def _run():
        root = find_project_root()
        job = require_job(root, asset_id)
        report = job.load_validation()
        if report is None:
            raise MasonError(
                "No validation.json; run mason build first.",
                code="no_validation",
            )
        _emit(
            json_mode,
            report.model_dump(),
            lambda: typer.echo(
                "passed" if report.passed else "failed",
            ),
        )
        if not report.passed:
            raise typer.Exit(code=1)

    _guard(json_mode, _run)


@app.command("list")
def list_cmd(json_mode: JsonFlag = False) -> None:
    """List jobs in this project."""

    def _run():
        root = find_project_root()
        jobs = list_jobs(root)
        payload = []
        for job in jobs:
            spec = job.load_spec()
            result = job.load_result()
            payload.append({
                "id": spec.id,
                "type": spec.type,
                "name": spec.name,
                "validation_passed": (
                    result.validation.get("passed") if result else None
                ),
            })
        _emit(
            json_mode,
            {"jobs": payload},
            lambda: print_list(jobs),
        )

    _guard(json_mode, _run)


@tools_app.command("scan")
def tools_scan(json_mode: JsonFlag = False) -> None:
    """Rediscover tools and store new paths in machine config."""
    tools = scan_and_store()
    payload = doctor_payload(tools)
    payload["success"] = True
    _emit(json_mode, payload, lambda: print_doctor(tools))


@config_app.command("get")
def config_get(
    key: Annotated[str, typer.Argument()],
    json_mode: JsonFlag = False,
) -> None:
    """Read a dotted machine-config key."""

    def _run():
        value = get_dotted(load_machine_config(), key)
        _emit(
            json_mode,
            {"key": key, "value": value},
            lambda: typer.echo("" if value is None else str(value)),
        )

    _guard(json_mode, _run)


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument()],
    value: Annotated[str, typer.Argument()],
    json_mode: JsonFlag = False,
) -> None:
    """Set a dotted machine-config key (tools.<name>.path)."""

    def _run():
        config = set_dotted(load_machine_config(), key, value)
        path = save_machine_config(config)
        _emit(
            json_mode,
            {"success": True, "key": key, "value": value, "path": str(path)},
            lambda: typer.echo(f"Wrote {path}"),
        )

    _guard(json_mode, _run)
