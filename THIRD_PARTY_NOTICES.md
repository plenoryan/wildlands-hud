# Third-party components

Wildlands HUD source is licensed under GPL-2.0-or-later. See [LICENSE](LICENSE).

## miniLZO 2.10

The bundled `minilzo.dll` is compiled from the unmodified upstream miniLZO 2.10
sources in [third_party/minilzo](third_party/minilzo). Copyright and license
notices are preserved in those source files and `COPYING` (GPL-2.0-or-later).
Upstream project: <https://www.oberhumer.com/opensource/lzo/>.

From a 64-bit MinGW-w64 shell at the repository root:

```sh
gcc -O2 -shared -static-libgcc third_party/minilzo/minilzo.c -o minilzo.dll
```

## Windows application runtime

The executable bundles Python, its standard runtime dependencies, Tcl/Tk, and
the PyInstaller bootloader. `build_portable.py` includes available upstream
runtime notices in each executable release under `third_party/runtime_notices`.
Their licenses remain those of their respective authors. The PyInstaller
bootloader exception is included in its upstream notice.

## Game resources

No Ghost Recon Wildlands archives, extracted textures, saves, fonts or other
game assets are distributed. Resource names, IDs, checksums and patch offsets
identify the local resources that this tool knows how to modify.

Ghost Recon Wildlands and associated marks belong to Ubisoft. This is an
independent community project and is not affiliated with or endorsed by Ubisoft.

