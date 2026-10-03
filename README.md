# Wildlands HUD

Choose what to hide with checkboxes. **Checked = hide; unchecked = keep.** The version picker has been removed. Downed-ally indicators and interaction prompts are always preserved.

[Download v0.6.0](https://github.com/plenoryan/wildlands-hud/releases/download/v0.6.0/WildlandsHUD.zip) · [Website](https://plenoryan.github.io/wildlands-hud/) · [Changelog](CHANGELOG.md)

## Default selection

| Option | Default |
| --- | --- |
| Enemies: icons, names, distances and pulses | Hide |
| Objects: generators, alarms, mines and similar | Hide |
| Normal allies: icons, names and distances | Hide |
| Other markers: objectives, collectibles, pings and sync shot | Hide |
| Minimap | Keep |
| Crosshair | Keep |
| Binocular and drone information | Keep |
| Weapon and ammunition information | Keep |

The objects option also covers player mines and other objects grouped by the game. Equipment types are not separate checkboxes. Binoculars and drones share elements and use one option. Other markers includes objectives and collectibles; uncheck it to retain them.

## Install and upgrade

1. Extract the ZIP and close the game.
2. Run `WildlandsHUD.exe` and choose your game folder. Run as administrator if write permission is required.
3. Review the checkboxes and click **Aplicar mod** (Apply). **Voltar à seleção padrão** resets the choices only; Apply writes them.
4. To upgrade V3/V4/V5 or change choices, apply again. The installer uses verified original backups and records options in the manifest. Select the previous manifest under **Já uso o mod** if prompted.

**Restaurar originais** restores the original interface. Keep `.phoenixhud.original` files beside the game and installation records in `%LOCALAPPDATA%\WildlandsHUD`. Unknown game versions or externally changed files are refused.

## Validation and limitations

- Windows 64-bit, your own game installation and about 9 GB free space. The executable includes Python.
- Defaults retain binocular, drone, crosshair, minimap, ammunition and interaction UI. When normal allies are hidden, downed ally names/distances are hidden too; the symbol/gauge and conditional off-screen arrows remain.
- The configurable edition is experimental and still needs gameplay confirmation. Binary tests do not prove every visual game state.
- Hidden images use an existing transparent game resource. Configurable mode modifies no shared textures.
- No game files, extracted assets, textures or saves are included. Each player uses their own installation.

## Development

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -v
python portable_hud.py --self-check self_check.json
python build_portable.py --format exe --output dist_custom
```

Private game fixtures are not distributed; tests requiring them skip in public CI.

[Disclaimer](DISCLAIMER.md) · [GPL-2.0-or-later](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)
