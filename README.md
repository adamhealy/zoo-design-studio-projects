# Zoo Design Studio projects

CAD parts modelled in [KCL](https://zoo.dev/docs/kcl-lang), Zoo's code-based
CAD language, for [Zoo Design Studio](https://zoo.dev/design-studio).

Each project is its own folder:

```
bracket-design/
  main.kcl            the model (open this folder in Design Studio)
  project.toml        Design Studio project settings
  bracket-design.stl  STL exported from main.kcl
```

The repo also includes an [Agent Skill](https://agentskills.io) at
[.agents/skills/kcl](.agents/skills/kcl/SKILL.md). It teaches a coding agent
how to write, check, render and export KCL with the tools below. Agents that
read `.agents/skills/` (such as Amp, Codex, Cursor and OpenCode) pick it up
directly; `.claude/skills/kcl` is a symlink to the same folder for Claude
Code. Edit the files under `.agents/skills/kcl`.

## Setup

You need three things: Design Studio to view and edit models, the `zoo` CLI
for command-line checks and exports, and the zoo MCP server so your agent can
run models directly. The CLI and MCP server are optional if you only use
Design Studio.

### 1. Zoo Design Studio

Download the desktop app for macOS, Windows or Linux from
**https://zoo.dev/design-studio/download** (also linked from
https://zoo.dev/design-studio). It's free to download. Sign up at
https://zoo.dev/signup if you don't have a Zoo account.

- **macOS:** open the `.dmg` and drag Zoo Design Studio to Applications.
- **Windows:** run the `.exe` installer.
- **Linux:** download the `.AppImage` for your architecture (x86-64 or
  ARM64), make it executable with `chmod +x`, then run it.

There's also a browser build at https://app.zoo.dev.

To work on a project, open its folder (e.g. `bracket-design/`) in Design
Studio.

### 2. The `zoo` CLI

On macOS, install it with Homebrew:

```bash
brew tap kittycad/kittycad
```

```bash
brew install kittycad
```

On Windows and Linux, follow the instructions on the
[latest release](https://github.com/KittyCAD/cli/releases). See the
[CLI README](https://github.com/KittyCAD/cli#installing) for details.

Then log in to your Zoo account and check it worked:

```bash
zoo auth login
```

```bash
zoo auth status
```

Commands that run a model (`zoo kcl volume`, `snapshot`, `export`) send it
to Zoo's servers, so they need this login. `zoo kcl format` and
`zoo kcl lint` work offline. Full reference: the
[CLI manual](https://zoo.dev/docs/developer-tools/cli/manual).

### 3. The zoo MCP server

[zoo-mcp](https://github.com/KittyCAD/mcp) is an MCP server that lets an
agent run KCL, render snapshots, measure and export models, and look up the KCL
docs and samples.

1. **Install uv**, which runs the server. On macOS:

   ```bash
   brew install uv
   ```

   For other platforms, see the
   [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

2. **Log in to Zoo.** This is separate from the CLI login and is saved in
   your system keychain (macOS Keychain, Windows Credential Locker or a
   Linux keyring):

   ```bash
   uvx zoo-mcp auth login
   ```

   ```bash
   uvx zoo-mcp auth status
   ```

   On a headless machine, use `uvx zoo-mcp auth login --no-browser`. You can
   also skip the login and set the `ZOO_API_TOKEN` environment variable to
   an API key from https://zoo.dev/account.

3. **Add it to your agent** as a stdio MCP server named `zoo` that runs
   `uvx zoo-mcp`. For example, in Claude Code:

   ```bash
   claude mcp add --scope user zoo -- uvx zoo-mcp
   ```

   Most other agents take the same command in their MCP config, e.g.
   `{"zoo": {"command": "uvx", "args": ["zoo-mcp"]}}`. Naming it `zoo`
   keeps the tool names short; the skill refers to them by their bare names
   (`evaluate_kcl`, ...).

4. **Check it's connected.** List your agent's MCP servers (e.g.
   `claude mcp list`) and look for `zoo`, or start the agent in this repo
   and ask it to test the zoo MCP.

For prebuilt binaries, client-specific setup and the full list of
environment variables, see the
[zoo-mcp README](https://github.com/KittyCAD/mcp).

## Working with an agent

Start your agent from the root of this repo so it finds the kcl skill. When
you ask for a change to a model, the agent edits `main.kcl` and checks it
with the zoo MCP (or the CLI if the MCP isn't connected). The checks are
format, lint, run, render, constraint status and measurements. It then
re-exports the project's STL so it matches the model. Open the project in
Design Studio to review the result.
