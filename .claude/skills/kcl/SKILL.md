---
name: kcl
description: Write, edit, check and render KCL (Zoo's CAD language) models for Zoo Design Studio, using the zoo MCP server's tools (mcp__zoo__*) or the `zoo` CLI to format, lint, run, snapshot, measure and export them. Use whenever a task touches a .kcl file or project.toml, asks to model, redesign or modify a CAD part in KCL, converts or measures an STL or other mesh, or mentions Zoo Design Studio, KittyCAD, the zoo MCP or the zoo CLI.
---

# KCL modelling with Zoo

Everything below was confirmed against Zoo Design Studio, the zoo MCP server
and `zoo` CLI 0.2.213 in November 2026, using KCL 3.0. Treat anything not
listed here as unverified: check it in the docs, then confirm it with the
checks below.

## Repo layout

This skill lives at the root of the `zoo-design-studio-projects` repo and
applies to every project in it. Each project is its own folder (e.g.
`bracket-design/`) holding a `main.kcl` and `project.toml`. Work out which
project the task is about first. Then run CLI commands from inside that
folder, and give the MCP tools absolute paths. The helper script is at
`.claude/skills/kcl/scripts/measure_stl.py` from the repo root.

## Prefer the zoo MCP, fall back to the CLI

When `mcp__zoo__*` tools are in the session, use them for checking, rendering,
measuring and docs lookup. They return structured results and images
directly, with no PNG files to Read. The tools are deferred, so load the ones
you need in one call first, e.g.
`ToolSearch("select:mcp__zoo__format_kcl,mcp__zoo__lint_and_fix_kcl,mcp__zoo__mock_execute_kcl,mcp__zoo__evaluate_kcl,mcp__zoo__calculate_cad_physical_properties")`.
If the zoo server isn't connected, use the CLI workflow further down.

Always save the KCL to disk with Edit/Write first, then pass `kcl_path`
(absolute path to `main.kcl` or the project folder). Passing `kcl_code`
runs the code without saving it anywhere.

### MCP workflow: check every edit

1. **Format:** `format_kcl(kcl_path=...)` rewrites the file in place and
   reports syntax errors. With `kcl_code` it returns the formatted text
   instead.
2. **Lint:** `lint_and_fix_kcl(kcl_path=...)` **also rewrites the file in
   place**, applying automatic fixes, then returns a list of lints it
   couldn't fix (empty when clean). Check `git diff` if it may have
   changed something.
3. **Quick run:** `mock_execute_kcl(kcl_path=...)` runs the language
   without building geometry. It catches undefined names (confirmed:
   "undefined value: `missingName` is not defined", with line and column)
   but not geometry failures.
4. **Full check in one call:** `evaluate_kcl` runs the model on Zoo's
   engine once and collects everything requested:

   ```
   evaluate_kcl(
     kcl_path = "<abs>/main.kcl",
     physical_properties_request = {"properties": ["volume"], "unit_volume": "mm3"},
     snapshot_request = {"views": ["isometric", "front", "top", "right"]},
     exports = [{"format": "stl", "destination_dir": "<scratchpad>/export-N"}],
   )
   ```

   - It returns mock and real execution status, the volume, inline images
     (1–4 views; `{}` gives one isometric) and the exported file paths.
   - It also reports each sketch as fully, under or over constrained, with
     free and conflict counts. Mention any under or over constrained
     sketches to the user.
   - Each export format needs its own new folder (use the scratchpad).
     Existing files aren't overwritten, so use a fresh folder each run.
   - **Don't trust its `bounding_box`.** It has the same bug as the CLI
     (168 × 32.75 × 10 mm for a part that is 140 × 28 × 9 mm).
5. **Measure the export:** run `calculate_bounding_box_cad` or
   `calculate_cad_physical_properties` on the exported STL. These give
   the true size (confirmed against `measure_stl.py`), plus volume, mass,
   surface area and centre of mass. Mass needs a density, e.g. 2700 kg:m3
   for aluminium or 1240 kg:m3 for PLA.
6. **Update the project's STL** once the checks pass: copy the STL that
   step 4 exported over the project's tracked STL. See "Finish: update the
   STL and commit" below.

### MCP: inspecting a model interactively

For several snapshots from custom angles, or to query edges and faces, use a
persistent session:

1. `start_modeling_session()` gives a session ID. Only one can be open at
   a time, and it never expires on its own.
2. `execute_kcl(kcl_path=..., session_id=...)` builds the scene and returns
   the path of an artifact-graph JSON file holding the entity IDs that the
   query tools take (`edge_get_length`, `entity_distance`,
   `get_face_info`, etc.).
3. `snapshot(session_id, camera_view=...)` renders the scene. Use a named
   view, `"multiview"` (front/right/top/iso collage),
   `"multi_isometric"`, or a `{"up", "vantage", "center"}` dict. Add
   `highlight_edges=true` to outline edges.
4. **Always** `stop_modeling_session(session_id)` when done, even after
   an error.

### MCP: docs and examples

- `lookup_kcl_docs(query)` searches the KCL reference and returns compact
  sections with examples. Use it before fetching zoo.dev pages. Expand
  truncated results with `get_kcl_doc(path)`.
- `search_kcl_samples(query)` finds example models, and
  `get_kcl_sample(name)` returns their full source. Check them before
  inventing a technique.

### MCP: tools that touch the user's Zoo account

The cloud project tools (`list_cloud_projects`, `project_write_file`,
`project_rm`, ...), job executions and org datasets read or change the
user's Zoo account. Read-only calls are fine when the task needs them. Ask
before any write, delete or job submission. `list_org_skills` returns
HTTP 403 for this account, so don't rely on org skills.

## CLI workflow: check every edit

Use this when the zoo MCP isn't available.
Run these after each change to a .kcl file, in order. Steps 1–2 work offline.
Steps 3–5 send the model to Zoo's servers and need `zoo auth login`
(`zoo auth status` shows whether you're logged in).

1. **Syntax check:** `zoo kcl format -w main.kcl`. This parses the file,
   reports syntax errors such as "Missing comma between arguments", and
   rewrites the file in the standard layout. Use `zoo kcl format main.kcl`
   (no `-w`) to preview the changes without writing them. The formatter
   always puts two blank lines after a comment that ends a block; leave
   them.
2. **Style check:** `zoo kcl lint -s main.kcl`. Prints nothing when the
   file is clean. Neither format nor lint runs the model, so neither
   catches undefined names, solver errors or failed booleans.
3. **Run the model:** `zoo kcl volume main.kcl --output-unit mm3 -f json`.
   This catches errors that only show up when the model runs, e.g.
   "KCL execution failed: undefined value: `x` is not defined". The volume
   it reports is accurate, so compare it with a hand estimate.
4. **Look at it:** `zoo kcl snapshot main.kcl <scratchpad>/iso.png --angle iso`,
   then Read the PNG. Other angles are `front`, `top`, `right-side` and
   `four-ways`. Save snapshots in the scratchpad, not the project.
5. **Measure it:** `zoo kcl export main.kcl <scratchpad>/export --output-format stl`,
   then `python3 -I <repo root>/.claude/skills/kcl/scripts/measure_stl.py <scratchpad>/export/output.stl`.
   That prints the true size and volume.
   - **Don't trust `zoo kcl bounding-box`.** For a part that measured
     140 × 28 × 9 mm in the export, it reported 168 × 32.75 × 10 mm.
     Use the export instead.
   - To check a cross-section, slice the exported STL with numpy and
     matplotlib through `uv run -q --with numpy --with matplotlib python -I script.py`.
6. **Update the project's STL** once the checks pass: copy the STL that
   step 5 exported over the project's tracked STL. See "Finish: update the
   STL and commit" below.

Before reporting dimensions, re-read the parameters in the file. The user
edits them in Design Studio between turns.

## Finish: update the STL and commit

Each project keeps an STL of its current model in git, named after the
project folder (e.g. `bracket-design/bracket-design.stl`). Keep it in step
with `main.kcl`, so every commit that changes the model also carries the
matching STL.

1. **Export from the saved file** after the last edit passes every check.
   Both `evaluate_kcl` and `zoo kcl export` write `output.stl` into a new
   scratchpad folder, and `evaluate_kcl` won't overwrite an existing file.
   Zoo writes ASCII STL in mm, the same format as the tracked files.
2. **Measure it** with `measure_stl.py` or the MCP measuring tools, and
   check the size and volume match the parameters.
3. **Copy it over the tracked STL:**
   `cp <scratchpad>/<export dir>/output.stl <project>/<project>.stl`.
4. **Check git sees the change you expect.** Use
   `cmp -s <new> <old>` or `git status`. A change that doesn't move any
   geometry, such as swapping constraints, gives a byte-identical STL
   (confirmed), so there's nothing new to commit. Say so rather than
   leaving it out silently.
5. **Commit the STL together with the .kcl change** it came from, when the
   user asks for a commit. Don't make a separate STL-only commit for a
   model change.

## File header

```kcl
@settings(defaultLengthUnit = mm, kclVersion = 3.0)
```

With `defaultLengthUnit = mm`, plain numbers mean mm. Angles always need a
unit, e.g. `90deg`. `project.toml` sits next to `main.kcl`, and the CLI
picks it up automatically.

## Use sketch blocks, not the pipe syntax

The old pipe syntax (`startSketchOn(XY) |> startProfile(...) |> line(...) |> close()`)
still works in 3.0 but gives deprecation warnings. Use sketch blocks:

```kcl
profile = sketch(on = XY) {
  bottom = line(start = [-a, -b], end = [a, -b])
  rightEnd = arc(start = [a, -b], end = [a, b], center = [a, 0]) // CCW by default
  top = line(start = [a, b], end = [-a, b])
  leftEnd = arc(start = [-a, b], end = [-a, -b], center = [-a, 0])
}
body = extrude(region(segments = [profile.bottom, profile.rightEnd]), length = 4)
```

Confirmed rules:

- **Fixed points are fine.** Points can be plain expressions of top-level
  variables. A loop closes if consecutive endpoints use identical
  expressions; it doesn't need `coincident`.
- **Arcs.** Use `arc(start, end, center)`. It sweeps counterclockwise by
  default; add `direction = CW` to go the other way.
- **Regions.** `region(segments = [s1, s2])` takes two segments that meet,
  in counterclockwise order around the loop. Draw loops counterclockwise
  in sketch coordinates.
- **Each region can be used once.** Every extrude or revolve consumes
  its region, so call `region(...)` again on the same sketch for a second
  copy.
- **Plane axes:**
  - `XY`: sketch x = X, sketch y = Y.
  - `YZ`: sketch x = global Y, sketch y = global Z (extrudes along +X).
  - `XZ`: sketch x = global X, sketch y = global Z.
  - `revolve(region(...), axis = Y)` on an XZ sketch spins around global Z.

### Constraint (solver) sketches

These also work and render. One sketch can mix fixed points with `var`
points:

```kcl
plate = sketch(on = XY) {
  bottom = line(start = [var -58mm, var -12mm], end = [var 58mm, var -12mm])
  rightEnd = arc(start = [var 58mm, var -12mm], end = [var 58mm, var 12mm], center = [halfStraight, 0])
  // ...top, leftEnd...
  coincident([bottom.end, rightEnd.start])   // join segments
  vertical([bottom.end, rightEnd.center])    // point straight below the centre
  radius(rightEnd) == halfWidth              // a variable on the right works
}
```

- **Check the constraint status after every sketch edit.** `evaluate_kcl`
  reports it, or call `get_sketch_constraint_status(kcl_path=...)` alone.
  `visualize_sketch(sketch_name, kcl_path=...)` draws the sketch with free
  geometry in blue and fully constrained geometry in white. Aim for every
  sketch fully constrained, and tell the user about any that aren't.
- **`tangent()` leaves a sketch under-constrained.** A stadium outline
  using `coincident` + `tangent` + `radius` drew the right shape, but the
  solver reported all four segments as free. It stayed free even with the
  arc centres pinned by `coincident`. Replacing each `tangent` with
  `vertical([line.end, arc.center])` made it fully constrained, with an
  identical result. The general fix: pin where a tangent point sits
  (`vertical` or `horizontal` against the arc centre), not the tangency
  itself.
- **`horizontal` and `vertical` take a segment or a list of points,**
  including `arc.center`, `line.start` and `line.end`, and `ORIGIN`.
- **`var` takes a literal with a unit,** e.g. `var -58mm`, never an
  expression. It's only a starting guess. Changing the plate from 140 to
  180 mm long still solved correctly from the old guesses, but if a big
  change makes the solver land on the wrong shape, update the guesses.
- **Don't add redundant constraints.** If the existing constraints already
  imply something (e.g. a line between two points that are each directly
  below an arc centre at the same height is already horizontal), adding
  `horizontal()` as well risks an over-constrained error.

## Solids, booleans and placement (all confirmed)

```kcl
a = extrude(region(...), length = 20, symmetric = true) |> translate(x = -50)
b = revolve(region(...), axis = Y)
body = union([plateBody, hookLeft, hookRight])
part = subtract([body], tools = [cutA, cutB])
```

- **Through-cuts:** extrude the cutter longer than the part and centre it
  with `symmetric = true` (e.g. `length = 3 * thickness`), so it pokes
  out of both faces with no coplanar faces left behind.
- **Joining touching parts:** sink the added part about 1 mm into the base
  (an `overlap`) so the union shares volume rather than a single face.
- **Repeated features:** draw the sketch once, then extrude it twice and
  `translate` each copy. That's simpler than `fn`, and sketch blocks
  inside `fn` haven't been tested yet.

## Style for this user

- They're learning KCL, so explain the concepts used in each change.
- Put named parameters at the top, then derived values, then sketches.
  Write a short comment per section saying which plane maps to which
  global axes.
- Ask the user to confirm the render in Design Studio as well. The MCP or
  CLI checks above are the first pass.

## Converting an STL to KCL

- **Get the targets first.** Run `calculate_cad_physical_properties` (MCP)
  or `measure_stl.py` on the original STL to get the size and volume the
  KCL model must match.
- **Read it with a script.** Binary STLs are too big to Read directly, so
  parse them with `struct` in a script run with `python3 -I` and keep
  the script in the scratchpad.
- **Find the layers.** List the distinct Z levels and face normals.
- **Slice it.** Take sections at several Z heights, plus YZ/XZ sections
  through each feature, and plot them with matplotlib via `uv run`.
- **Model it centred on the origin,** then compare volume and size with
  the original, using the MCP measuring tools on an exported STL or
  `measure_stl.py`.

## References

- Language guide: https://zoo.dev/docs/kcl-lang
- KCL 3 migration (sketch blocks, regions, what changed): https://zoo.dev/docs/kcl-lang/migrating-to-kcl-3
- Sketch-solve tutorial: https://zoo.dev/docs/kcl-book/sketch2d_constraints.html
- Standard library reference: https://zoo.dev/docs/kcl-std (e.g. `functions/std-sketch-region`, `std-solver-arc`, `std-sketch-revolve`, `std-solid-subtract`)
- CLI manual: https://zoo.dev/docs/developer-tools/cli/manual
- Example models: https://zoo.dev/docs/kcl-samples and https://zoo.dev/aquarium
- zoo MCP server (installed as `zoo`, tools `mcp__zoo__*`): https://github.com/KittyCAD/zoo-mcp
