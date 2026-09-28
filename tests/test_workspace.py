"""mason init writes the same workflow into both agent files."""

from pathlib import Path

from mason.core.agent_workflow import MASON_WORKFLOW
from mason.core.workspace import END_MARKER, START_MARKER, init_project

ROOT = Path(__file__).resolve().parents[1]


def _block(text: str) -> str:
    start = text.find(START_MARKER)
    end = text.find(END_MARKER, start)
    assert start >= 0 and end > start
    stop = end + len(END_MARKER)
    return text[start:stop].strip()


def test_repo_agents_matches_workflow() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert _block(text) == MASON_WORKFLOW.strip()
    assert "## Stop early" in MASON_WORKFLOW


def test_init_writes_agents_and_claude(tmp_path: Path) -> None:
    init_project(tmp_path, name="game")
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert _block(agents) == MASON_WORKFLOW.strip()
    assert claude.strip() == MASON_WORKFLOW.strip()


def test_init_replaces_stale_workflow(tmp_path: Path) -> None:
    notes = "# House rules\n\nKeep the camera low.\n"
    stale = notes + "\n# Mason Agent Workflow\n\nold steps only\n"
    (tmp_path / "AGENTS.md").write_text(stale, encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(
        "Project notes.\n\n# Mason Agent Workflow\n\nstale\n"
        "# End Mason Agent Workflow\n\nMore notes.\n",
        encoding="utf-8",
    )
    init_project(tmp_path, name="game")
    init_project(tmp_path, name="game")
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert agents.count(START_MARKER) == 1
    assert agents.count(END_MARKER) == 1
    assert "old steps" not in agents
    assert "Keep the camera low." in agents
    assert _block(agents) == MASON_WORKFLOW.strip()
    assert "Project notes." in claude
    assert "More notes." in claude
    assert "stale" not in claude
    assert claude.count(START_MARKER) == 1
