# Contributing

Bug reports and pull requests are welcome in English or Portuguese.

## Report a problem

Use the [bug report form](https://github.com/plenoryan/wildlands-hud/issues/new?template=bug_report.yml). Include the app release, selected mode, Windows version, game storefront/build if known, steps to reproduce and the exact error text.

For V4 feedback, describe whether the ally was normal or downed, on-screen or off-screen, and whether the problem persisted after revival. Distinguish an in-game observation from a file check or automated test.

Do not attach `.forge` archives, extracted game resources or save files. They are not needed for an initial report. Redact personal paths or account details from error messages. If restoration fails, keep the original backups and installation records intact while investigating.

## Development setup

Use Windows 64-bit and Python 3.11 with Tcl/Tk, matching CI:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m unittest discover -v
.\.venv\Scripts\python portable_hud.py --self-check self-check.json
```

The public repository includes `minilzo.dll` and its corresponding source under `third_party/minilzo`. See the README for rebuilding it with a Windows 64-bit GCC toolchain.

Synthetic fixtures belong in tests. Proprietary game fixtures do not belong in the repository, pull requests or release assets. Tests that depend on those fixtures skip when they are absent; do not present the public test run as the full internal fixture-based test suite.

## Patch boundaries

- Select targets explicitly and verify their original hashes. Do not bypass unknown-resource rejection to claim support for another game version.
- Preserve resource identities, sizes, dependencies, headers, bindings and animations except for a documented, precisely scoped change.
- Preserve unrelated resources and shared HUD elements. V4 must retain the downed-ally gauge and both conditional off-screen arrows.
- Preserve original backups and verified restore behavior. Do not overwrite unknown changes, partial files or previous backups to force an installation through.
- Keep build inputs on an explicit code/dependency allowlist. Never package the game archives, extracted resources, caches or prepared game packages.

Changes to a visual behavior need an in-game report before documentation calls that behavior confirmed. Automated tests and a successful executable self-check cannot establish what the game renders.

## Build verification

Build into a new output directory; the build refuses to replace an existing distribution:

```powershell
.\.venv\Scripts\python build_portable.py --format exe --output dist_review
```

Run `dist_review\WildlandsHUD\WildlandsHUD.exe` with `--self-check` and an output JSON path to verify the bundled runtime. This check does not open a game installation. The normal interface can also be opened for a manual layout check.

CI runs the public tests, checks the source runtime, builds the executable and checks the frozen runtime. It does not publish a release or validate behavior inside the game.

## Pull requests

Describe the concrete problem, resulting behavior and relevant validation. For a patch change, identify affected resource IDs/properties and explain what remains preserved. Include test results and explicitly state any behavior that still needs gameplay verification. Keep the English and Portuguese READMEs consistent when changing user-facing behavior.

Contributions are made under the project’s [GNU GPL version 2 or later](LICENSE). Keep third-party sources and their license notices with any distributed build.
