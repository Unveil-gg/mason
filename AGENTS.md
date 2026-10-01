# Agent instructions

## Style
Follow the language’s [Google Style Guide](https://google.github.io/styleguide/).
Lua: [Roblox](https://roblox.github.io/lua-style-guide/). OCaml: [Jane Street](https://opensource.janestreet.com/standards/).
- 80 cols (hard cap 100). Simple over clever. No new patterns if existing ones work.
- Brief function comments: usage, params, returns.

## Changes
Surgical only. Min files/lines. No drive-by refactors, extra docs, or unrelated cleanup.

## After code
If this turn generated or edited code, end with a suggested commit message (1–2 sentences, why not what). Do not commit unless asked.

## Mason
Asset builds go through the Mason skill at `skills/mason/SKILL.md`.
`mason init` installs that skill into a game project.
`mason init --global` installs it for this user.
`mason workflow` prints the directed loop.
Do not paste that loop into `AGENTS.md` or `CLAUDE.md`.
