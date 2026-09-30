# Changelog

## v0.4.0 — 2026-09-30 — Prerelease

First public source and Windows executable release of Wildlands HUD.

### Included

- A portable Windows 64-bit application with an embedded Python runtime, a game-folder picker, V3/V4 selection and restoration of verified original files.
- **V3:** targeted enemy marker suppression, including the icons, distance labels, circles and pulses confirmed in a reported gameplay test.
- **V4:** V3 plus normal ally marker suppression. The downed-ally gauge/symbol remains; the two off-screen arrows are conditional on the ally being downed and off-screen. Ally names and distances remain hidden even while downed.
- Preparation from each player’s own installation, exact resource-hash checks, original-file backups and installation records used for restoration.
- Public source, a build script, dependency sources/notices, English and Brazilian Portuguese documentation, and Windows CI for public tests and runtime checks.

### Validation and limitations

- **V4 is experimental.** Its additional ally behavior has not yet been confirmed in gameplay. Test downed allies both on-screen and off-screen, and check the state after revival.
- V3’s reported gameplay confirmation is not a guarantee for every game state or game version. Compatibility depends on recognized resource hashes.
- Public tests do not distribute proprietary fixtures. Tests needing absent game fixtures are skipped, so a public CI run does not represent the complete internal fixture-based suite.
- Installation and restoration refuse unknown file changes. Some interrupted installations may require manual recovery with the preserved backups and records.
- No game archives, extracted game resources, textures or saves are included in the release.
