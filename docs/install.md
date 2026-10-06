# Install and setup

Prefer [uv](https://docs.astral.sh/uv/). `uv tool install` puts
`mason` on PATH. Open a new terminal if the current one cannot see it.

## Use Mason in a game

Install the CLI once, then work in the game repo. A public clone
needs no extra GitHub login. If this repo is private, use
`gh auth login` or another credential helper first.

```bash
uv tool install "git+https://github.com/Unveil-gg/mason.git"
mason doctor
```

`mason doctor` looks for Blender in machine config, then on PATH,
then in common install folders (`Program Files/Blender Foundation`,
`/Applications/Blender.app`, `/usr/bin/blender`). Set a path only
when doctor does not find it. The version folder on Windows is
whatever you installed:

```bash
mason config set tools.blender.path "C:/Program Files/Blender Foundation/Blender 4.2/blender.exe"
mason config set tools.blender.path "/Applications/Blender.app/Contents/MacOS/Blender"
```

Krita, Aseprite, and ImageMagick are optional. Doctor finds them
the same way (`krita` or `kritarunner`, `magick` then `convert`,
`aseprite`). After you install one later, run `mason tools scan`.

Machine config is `%APPDATA%/Mason/config.yaml` on Windows and
`~/.config/mason/config.yaml` on macOS and Linux. Keep those paths
out of asset specs.

In the game repo:

```bash
mason init
```

That writes `mason.yaml`, adds `.mason/` to an existing
`.gitignore`, and installs the Mason skill into
`.agents/skills/mason` (linked for Cursor and Claude, or copied
if the OS refuses the link). It does not edit `AGENTS.md`. Run
`mason init` again after a Mason upgrade to refresh the skill.
An existing `mason.yaml` and any `styles/` files are left as they
are. The `default` style is built into the CLI; add
`styles/<name>.yaml` only for a project look.

`mason init --global` installs the skill for your user and skips
project files.

## Agent skill ([skills.sh](https://skills.sh))

There is no separate publish step. The skill lives in this repo at
`skills/mason/`. Anyone with repo access installs it with the
[Vercel skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add Unveil-gg/mason              # this project
npx skills add Unveil-gg/mason -g           # all projects (this user)
npx skills add Unveil-gg/mason -s mason -y  # non-interactive, mason only
npx skills add Unveil-gg/mason --list       # list skills in the repo
```

The skill installs the CLI if `mason` is missing, runs `mason init`
when there is no `mason.yaml`, then builds from the user's request.
`mason init` copies the same skill into the project and refreshes it
on upgrade.

Listing on [skills.sh](https://skills.sh) comes from `npx skills add`
telemetry, not a submit form. Other machines and people count;
repeating the command on one machine barely does. A public repo
helps. A private repo still installs with GitHub auth.

## Develop Mason

```bash
git clone https://github.com/Unveil-gg/mason.git
cd mason
uv sync
uv run mason doctor
uv tool install --editable .
```

`--editable` keeps the PATH command on this clone after you pull.
`pip install -e ".[dev]"` is the same idea without uv.

## External tools

| Tool | Used for |
| --- | --- |
| Blender 4+ | `static_prop` → `.blend` / `.glb` and previews |
| Krita | `layered_raster` → `.kra` + PNG |
| Aseprite | `sprite_sheet` → PNG + `frames.json` |
| ImageMagick | `image_process` (resize, quantize, …) |
