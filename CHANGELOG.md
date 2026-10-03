# Changelog

## v0.6.0 — 2026-10-03 — Configurable HUD (experimental)

- Replaces the version picker with eight checkboxes. Checked hides a group; unchecked retains it. Defaults hide enemies, objects, normal allies and other world markers. Operational HUD is retained.
- Always retains downed-ally indicators and contextual interaction prompts. Binocular/drone information is one group because they share widgets. Objects includes player mines and other game-grouped objects.
- Uses the original, independently decoded transparent 4x4 image. No shared texture edits, so hiding one category does not blank another category’s enemy detection image.
- Records selections in the manifest/receipt and supports upgrades from older versions using verified original backups. New edition still needs gameplay confirmation.

## v0.5.1 — 2026-10-02 — Interaction prompt fix

- Fixes the reported V5 regression that hid action prompts such as “press X”.
- Retains contextual interactions and control hints, plus their ancestor instances across base/patch archives. Other inspected HUD visuals remain suppressed, including generator markers; V4 downed-ally behaviour is unchanged.
- 516 additional HUD targets (545 total). Regression coverage checks that interaction and downed-ally display chains cannot be scaled away.
- Upgrade uses verified original backups, including when the active mode is already V5. Gameplay confirmation of this fix is pending.

## v0.5.0 — 2026-10-02 — Experimental prerelease

- New default V5 suppresses inspected HUD visuals, including object markers (generators, alarms, turrets, SAMs and jammers), names/distances, crosshair, minimap, ammunition and notifications.
- Keeps V4 downed-ally gauge and conditional off-screen arrows; no ally names/distances. V3/V4 remain selectable.
- Adds 529 hash-locked HUD resources to the existing 29 V4 changes. Preserves shared image/font assets and the full dependency chain leading to the downed gauge.
- Includes the bilingual disclaimer in the downloadable ZIP.
- Experimental: no V5 gameplay confirmation yet. Automated checks do not establish visual completeness or every game state.

## Documentation update — 2026-09-30

- Recorded the creator’s successful V4 gameplay test.
- Added a bilingual disclaimer to the website, documentation and release notes.
- The v0.4.0 executable and archive are unchanged.

## v0.4.0 — 2026-09-30 — Prerelease

First public source and Windows executable release of Wildlands HUD.

### Included

- A portable Windows 64-bit application with an embedded Python runtime, a game-folder picker, V3/V4 selection and restoration of verified original files.
- **V3:** targeted enemy marker suppression, including the icons, distance labels, circles and pulses confirmed in a reported gameplay test.
- **V4:** V3 plus normal ally marker suppression. The downed-ally gauge/symbol remains; the two off-screen arrows are conditional on the ally being downed and off-screen. Ally names and distances remain hidden even while downed.
- Preparation from each player’s own installation, exact resource-hash checks, original-file backups and installation records used for restoration.
- Public source, a build script, dependency sources/notices, English and Brazilian Portuguese documentation, and Windows CI for public tests and runtime checks.

### Validation and limitations

- **V4 gameplay confirmation (2026-09-30):** the creator reported that V4 was tested and worked. This is a reported gameplay result, not exhaustive validation of every game state or installation.
- Reported gameplay confirmations of V3 and V4 are not a guarantee for every game state or game version. Compatibility depends on recognized resource hashes.
- Public tests do not distribute proprietary fixtures. Tests needing absent game fixtures are skipped, so a public CI run does not represent the complete internal fixture-based suite.
- Installation and restoration refuse unknown file changes. Some interrupted installations may require manual recovery with the preserved backups and records.
- No game archives, extracted game resources, textures or saves are included in the release.
