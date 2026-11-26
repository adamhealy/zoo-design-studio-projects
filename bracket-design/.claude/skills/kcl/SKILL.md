---
name: kcl
description: Write, edit, check and render KCL (Zoo's CAD language) models for Zoo Design Studio, and use the `zoo` CLI to format, lint, run, snapshot and export them. Use whenever a task touches a .kcl file or project.toml, asks to model, redesign or modify a CAD part in KCL, converts an STL or other mesh into KCL, or mentions Zoo Design Studio, KittyCAD or the zoo CLI.
---

# KCL modelling with Zoo

Everything below was confirmed against Zoo Design Studio and `zoo` CLI 0.2.213
in November 2026, using KCL 3.0. Treat anything not listed here as unverified:
check it in the docs, then confirm it with the checks below.

## Workflow: check every edit

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
   then `python3 -I .claude/skills/kcl/scripts/measure_stl.py <scratchpad>/export/output.stl`.
   That prints the true size and volume.
   - **Don't trust `zoo kcl bounding-box`.** For a part that measured
     140 × 28 × 9 mm in the export, it reported 168 × 32.75 × 10 mm.
     Use the export instead.
   - To check a cross-section, slice the exported STL with numpy and
     matplotlib through `uv run -q --with numpy --with matplotlib python -I script.py`.

Before reporting dimensions, re-read the parameters in the file. The user
edits them in Design Studio between turns.

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
  tangent([bottom, rightEnd])                // smooth join
  radius(rightEnd) == halfWidth              // a variable on the right works
}
```

- **`var` takes a literal with a unit,** e.g. `var -58mm`, never an
  expression. It's only a starting guess, so after a big parameter change,
  update the guesses to roughly match.
- **Don't add redundant constraints.** For example, a line tangent to two
  equal arcs whose centres are level is already horizontal, so adding
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
- Ask the user to confirm the render in Design Studio as well. The CLI
  checks above are the first pass.

## Converting an STL to KCL

- **Read it with a script.** Binary STLs are too big to Read directly, so
  parse them with `struct` in a script run with `python3 -I` and keep
  the script in the scratchpad.
- **Find the layers.** List the distinct Z levels and face normals.
- **Slice it.** Take sections at several Z heights, plus YZ/XZ sections
  through each feature, and plot them with matplotlib via `uv run`.
- **Model it centred on the origin,** then compare volume and size with
  the original using `measure_stl.py`.

## References

- Language guide: https://zoo.dev/docs/kcl-lang
- KCL 3 migration (sketch blocks, regions, what changed): https://zoo.dev/docs/kcl-lang/migrating-to-kcl-3
- Sketch-solve tutorial: https://zoo.dev/docs/kcl-book/sketch2d_constraints.html
- Standard library reference: https://zoo.dev/docs/kcl-std (e.g. `functions/std-sketch-region`, `std-solver-arc`, `std-sketch-revolve`, `std-solid-subtract`)
- CLI manual: https://zoo.dev/docs/developer-tools/cli/manual
- Example models: https://zoo.dev/docs/kcl-samples and https://zoo.dev/aquarium
- Official MCP server (not installed): https://github.com/KittyCAD/zoo-mcp, with `execute_kcl`, `mock_execute_kcl`, `snapshot` and `get_kcl_sample` tools
