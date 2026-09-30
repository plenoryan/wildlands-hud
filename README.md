# Wildlands HUD

**A local HUD mod installer for Tom Clancy’s Ghost Recon Wildlands on Windows.** Hide enemy markers, or try hiding normal ally markers while retaining the downed-ally indicator.

[Português (Brasil)](README.pt-BR.md) · [Project website](https://plenoryan.github.io/wildlands-hud/) · [Download v0.4.0](https://github.com/plenoryan/wildlands-hud/releases/download/v0.4.0/WildlandsHUD.zip) · [Release notes](CHANGELOG.md)

**V3 and V4 have been confirmed working in reported gameplay tests by the creator.** v0.4.0 remains the first public prerelease; these reports do not establish compatibility with every installation, game version or game state.

## Choose a mode

| Mode | Behavior | Validation |
| --- | --- | --- |
| **V3 — enemies only** | Hides the targeted enemy icons, distance labels, circles and pulses. | Confirmed in a reported gameplay test. |
| **V4 — enemies and normal allies** | Includes V3 and hides normal ally markers, names and distances. Preserves the downed-ally gauge/symbol and makes the two off-screen arrows conditional on the ally being downed and off-screen. | Resource checks, automated tests and a reported gameplay confirmation by the creator. |

V4 also hides ally names and distances while they are downed. Preservation refers to the downed-ally gauge/symbol and conditional off-screen arrows, not those text labels. The tool targets inspected HUD resources; it does not claim to remove every marker category. Sync Shot markers are outside its target list.

## Install

You need **Windows 64-bit**, your own installation of Ghost Recon Wildlands, and roughly **9 GB of free space** for the first preparation. The downloadable executable includes its Python runtime; you do not need to install Python.

1. [Download WildlandsHUD.zip](https://github.com/plenoryan/wildlands-hud/releases/download/v0.4.0/WildlandsHUD.zip) and extract it completely.
2. Close Ghost Recon Wildlands.
3. Right-click `WildlandsHUD.exe` and choose **Run as administrator**.
4. Select your game’s installation folder.
5. Choose **V3** or **V4**, then click **Aplicar mod** (Apply mod). The current app interface is in Portuguese.
6. Wait for preparation, verification and installation to finish before starting the game.

For V4, check a normal ally, a downed ally on-screen, a downed ally off-screen and the state after revival. Report the result through [Issues](https://github.com/plenoryan/wildlands-hud/issues).

The app prepares the mod from your local game files. The download contains code, the executable and dependency notices/source; **it contains no game archives, extracted resources, textures or saves**. Every player prepares it from their own installation.

## Restore the original HUD

Close the game, open the app, select the same game folder and click **Restaurar originais** (Restore originals).

Original archives are kept beside the game files with the suffix `.phoenixhud.original`. Preparation files and installation records are kept in `%LOCALAPPDATA%\WildlandsHUD`. **Keep these backups and records while the mod is installed.** If you used an earlier package, select **Já uso o mod** and choose that package’s `manifest.json` when asked.

The app verifies hashes before installing or restoring. It refuses unknown changes instead of overwriting them. If an interrupted installation cannot be restored automatically, preserve the backups and records for recovery; some interruptions may need manual assistance.

## Compatibility and limits

- Compatibility is determined by the hashes of the inspected resources, not a promise of support for every game version or storefront.
- Unknown resource versions are rejected. A game update or another mod that changes the same archives can require a new compatibility review.
- Reported V3 and V4 gameplay confirmations do not validate every game state or version.
- Automated tests check file handling, patch boundaries and application behavior. They do not run the game or prove the rendered result.

## Run or build from source

The public CI uses **Python 3.11, 64-bit, on Windows**. Source execution needs Python with Tcl/Tk and the included `minilzo.dll`.

```powershell
py -3.11 portable_hud.py
```

To build the standalone ZIP, use a fresh output directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python build_portable.py --format exe --output dist_release
```

The output is `dist_release\WildlandsHUD.zip`. The build includes the application source, license and third-party materials. A source-only package is also available with `--format source`.

To rebuild miniLZO using a Windows 64-bit GCC toolchain, run from the repository root:

```powershell
gcc -O2 -shared -static-libgcc third_party/minilzo/minilzo.c -o minilzo.dll
```

## Tests and contributions

```powershell
.\.venv\Scripts\python -m unittest discover -v
.\.venv\Scripts\python portable_hud.py --self-check self-check.json
```

Public tests use synthetic data where possible. Tests requiring proprietary game fixtures are skipped when those files are absent; the fixtures are not distributed. CI also builds the executable and checks its bundled runtime without opening or changing a game installation. A passing CI run is not in-game validation.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the patching constraints and how to report a problem.

## Disclaimer

Use this mod at your own risk. It is provided **as is, without warranty**. To the extent permitted by applicable law, the author and contributors are not liable for damage or loss arising from its use, including file/save loss, game failures or platform sanctions. Keep your backups and follow the game and platform rules. See the [full disclaimer](DISCLAIMER.md), which preserves mandatory legal rights and the GPL terms.

## License

Wildlands HUD is distributed under **GNU GPL version 2 or later**; see [LICENSE](LICENSE). miniLZO source and its license are included under [third_party/minilzo](third_party/minilzo). Packaged runtime components retain their own notices.

This is an independent community project, not an official Ubisoft product. Ghost Recon Wildlands and its game assets belong to their respective owners.
