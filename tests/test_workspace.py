"""mason init installs the skill and leaves agent files alone."""

from pathlib import Path

from mason import __version__
from mason.core.skill_install import skill_source
from mason.core.workspace import init_global, init_project

ROOT = Path(__file__).resolve().parents[1]


def test_skill_version_matches_package() -> None:
    text = (skill_source() / "SKILL.md").read_text(encoding="utf-8")
    assert f'mason_version: "{__version__}"' in text
    assert (skill_source() / "references" / "workflow.md").is_file()
    assert (skill_source() / "references" / "evaluate.md").is_file()


def test_repo_agents_points_at_skill() -> None:
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "skills/mason/SKILL.md" in text
    assert "# End Mason Agent Workflow" not in text


def test_init_installs_skill_not_agent_files(tmp_path: Path) -> None:
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# House rules\n", encoding="utf-8")
    created = init_project(tmp_path, name="game")
    assert agents.read_text(encoding="utf-8") == "# House rules\n"
    assert not (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / "styles" / "default.yaml").exists()
    skill = tmp_path / ".agents" / "skills" / "mason" / "SKILL.md"
    assert skill.is_file()
    assert (tmp_path / ".cursor" / "skills" / "mason" / "SKILL.md").is_file()
    assert (tmp_path / ".claude" / "skills" / "mason" / "SKILL.md").is_file()
    assert created["mason.yaml"].endswith("mason.yaml")
    assert (tmp_path / ".mason" / "jobs").is_dir()


def test_reinit_keeps_project_config_and_refreshes_skill(
    tmp_path: Path,
) -> None:
    init_project(tmp_path, name="game")
    config = tmp_path / "mason.yaml"
    config.write_text(
        "name: cafe\ndefault_style: cafe\ninstall_dir: res\n",
        encoding="utf-8",
    )
    marker = tmp_path / ".agents" / "skills" / "mason" / "extra.txt"
    marker.write_text("stale\n", encoding="utf-8")
    init_project(tmp_path, name="other")
    text = config.read_text(encoding="utf-8")
    assert "name: cafe" in text
    assert "other" not in text
    assert not marker.exists()
    skill = tmp_path / ".agents" / "skills" / "mason" / "SKILL.md"
    assert skill.read_text(encoding="utf-8") == (
        skill_source() / "SKILL.md"
    ).read_text(encoding="utf-8")


def test_init_gitignore_once(tmp_path: Path) -> None:
    ignore = tmp_path / ".gitignore"
    ignore.write_text("*.log")
    init_project(tmp_path, name="game")
    init_project(tmp_path, name="game")
    text = ignore.read_text(encoding="utf-8")
    assert text.count(".mason/") == 1
    assert text.startswith("*.log\n")


def test_init_skips_missing_gitignore(tmp_path: Path) -> None:
    init_project(tmp_path, name="game")
    assert not (tmp_path / ".gitignore").exists()


def test_init_global_writes_user_skill(tmp_path: Path) -> None:
    created = init_global(tmp_path)
    assert (tmp_path / "mason.yaml").exists() is False
    skill = tmp_path / ".agents" / "skills" / "mason" / "SKILL.md"
    assert skill.is_file()
    assert Path(created["skill"]) == skill.parent
    cursor = tmp_path / ".cursor" / "skills" / "mason" / "SKILL.md"
    claude = tmp_path / ".claude" / "skills" / "mason" / "SKILL.md"
    assert cursor.is_file()
    assert claude.is_file()
