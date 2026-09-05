"""Human-readable Rich output for Mason commands."""

from __future__ import annotations

from mason.core.jobs import AssetJob
from mason.core.results import BuildResult
from mason.core.workspace import find_project_root
from mason.tools.base import ToolInfo
from mason.tools.registry import ALL_CAPABILITIES, TOOL_GROUPS, capabilities_from
from rich.console import Console
from rich.table import Table

console = Console()


def _abs(rel_path: str) -> str:
    """Best-effort absolute path for a project-relative path string."""
    try:
        return str((find_project_root() / rel_path).resolve())
    except Exception:
        return rel_path


def print_doctor(tools: dict[str, ToolInfo]) -> None:
    console.print("[bold]Mason Environment[/bold]\n")
    labels = {
        "blender": "Blender",
        "krita": "Krita",
        "imagemagick": "ImageMagick",
        "aseprite": "Aseprite",
    }
    for group, ids in TOOL_GROUPS.items():
        console.print(f"[bold]{group}[/bold]")
        for tool_id in ids:
            info = tools[tool_id]
            name = labels[tool_id]
            if info.available:
                ver = f" {info.version}" if info.version else ""
                console.print(f"  [green]✓[/green] {name}{ver}")
            else:
                console.print(f"  [dim]○[/dim] {name} not found")
        console.print()
    caps = set(capabilities_from(tools))
    console.print("[bold]Available capabilities:[/bold]")
    for cap in ALL_CAPABILITIES:
        mark = "[green]✓[/green]" if cap in caps else "[dim]○[/dim]"
        console.print(f"  {mark} {cap}")


def print_build(result: BuildResult) -> None:
    status = "[green]ok[/green]" if result.success else "[red]failed[/red]"
    console.print(f"Built [bold]{result.asset_id}[/bold] ({status})")
    if result.outputs:
        console.print("Outputs:")
        for key, path in result.outputs.items():
            console.print(f"  {key}: {_abs(path)}")
    if result.previews:
        console.print("Previews:")
        for key, path in result.previews.items():
            console.print(f"  {key}: {_abs(path)}")
    passed = result.validation.get("passed")
    console.print(f"Validation: {'passed' if passed else 'failed'}")
    for key in ("triangles", "materials", "width", "height"):
        if key in result.validation:
            console.print(f"  {key}: {result.validation[key]}")


def print_inspect(job: AssetJob, result: BuildResult | None) -> None:
    spec = job.load_spec()
    console.print(f"[bold]{spec.id}[/bold]  ({spec.type})")
    console.print(f"  name: {spec.name}")
    console.print(f"  style: {spec.style}")
    if result:
        console.print(f"  tool: {result.tool} {result.tool_version or ''}")
        console.print(f"  built_at: {result.built_at}")
        console.print(f"  validation: {result.validation.get('passed')}")
        for key, path in result.outputs.items():
            console.print(f"  output.{key}: {_abs(path)}")
        for key, path in result.previews.items():
            console.print(f"  preview.{key}: {_abs(path)}")
        for key in ("triangles", "materials", "mesh_count", "width", "height"):
            if key in result.validation:
                console.print(f"  {key}: {result.validation[key]}")


def print_list(jobs: list[AssetJob]) -> None:
    table = Table(title="Mason jobs")
    table.add_column("id")
    table.add_column("type")
    table.add_column("validation")
    for job in jobs:
        spec = job.load_spec()
        result = job.load_result()
        passed = ""
        if result:
            passed = "passed" if result.validation.get("passed") else "failed"
        table.add_row(spec.id, spec.type, passed)
    console.print(table)


def print_init(created: dict[str, str]) -> None:
    console.print("Initialized Mason project")
    for key, path in created.items():
        console.print(f"  {key}: {path}")
