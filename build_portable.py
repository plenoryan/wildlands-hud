# SPDX-License-Identifier: GPL-2.0-or-later
"""Build a small shareable HUD app without redistributing game archives.

Run with the Python environment containing PyInstaller to build an executable.
--format source needs no extra dependency and creates a Python source package.
"""
import argparse
import importlib.metadata
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
README = """Wildlands HUD — aplicativo para uso local

1. Extraia esta pasta antes de abrir o aplicativo.
2. Feche Ghost Recon Wildlands.
3. Clique com o botão direito em WildlandsHUD.exe e use Executar como administrador.
   Na edição em Python, use Abrir_WildlandsHUD.cmd.
4. Escolha a pasta da sua própria instalação do jogo.
5. Marque o que deseja ocultar. Desmarcado significa manter.
6. Clique em Aplicar mod e aguarde a conferência terminar.

O padrão oculta inimigos, objetos, aliados normais e outros marcadores no cenário.
Mira, minimapa, binóculo/drone e munição ficam desmarcados e são preservados.
Aliado caído e avisos de interação são sempre preservados. A categoria Objetos
inclui equipamentos inimigos, minas próprias e outros objetos agrupados pelo jogo.
Binóculo e drone compartilham elementos e ficam na mesma opção.
O seletor de versões foi substituído pelas caixas. Para atualizar de V3/V4/V5,
use esta edição e aplique a seleção; ela usa os backups originais conferidos.
Esta edição ainda requer teste em partida, incluindo interação, binóculo e caído
dentro/fora da tela. Com aliados normais ocultos, nomes/distâncias dos caídos
também ficam ocultos; o símbolo/medidor e as setas condicionais são preservados.

Para desfazer, abra este aplicativo, escolha a mesma pasta e use Restaurar originais.
Ele só restaura arquivos reconhecidos; uma atualização do jogo ou outro mod pode
exigir nova análise, sem sobrescrever mudanças desconhecidas.

Na primeira aplicação reserve cerca de 9 GB livres. As cópias de preparo e o
manifesto ficam em %LOCALAPPDATA%\\WildlandsHUD; os originais ficam junto ao jogo,
com o sufixo .phoenixhud.original. Não apague esses registros/backups enquanto o
mod estiver instalado. Para atualizar um teste antigo feito por outra ferramenta,
use Já uso o mod e selecione o manifest.json do pacote anterior.

Cada amigo precisa preparar o mod a partir da própria instalação. Este arquivo
não inclui .forge, texturas, recursos extraídos, saves nem outros arquivos do jogo.
Versões de recursos diferentes das inspecionadas são recusadas com segurança.
Se faltar permissão para alterar a pasta do jogo, execute como administrador.

A edição em fontes precisa de Python 3.9 ou mais recente para Windows 64 bits,
com Tcl/Tk (incluído na instalação padrão do Python). Nenhum pacote pip é necessário.

Projeto e licença GPL-2.0-or-later: https://github.com/plenoryan/wildlands-hud
O código de miniLZO e sua licença estão em third_party/minilzo.
"""
LAUNCHER = """@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 portable_hud.py
    if errorlevel 1 pause
    exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
    python portable_hud.py
    if errorlevel 1 pause
    exit /b
)
echo Instale Python 3.9 ou mais recente, 64 bits, com Tcl/Tk, ou use a edicao executavel.
pause
"""


def source_files(root=ROOT):
    """Explicit code-only allowlist; never walk assets, prepared packages or games."""
    root = Path(root)
    paths = [root / "portable_hud.py", root / "forge_io.py", root / "minilzo.dll"]
    paths.extend(sorted(root.glob("phoenix_*.py")))
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError("Arquivo necessário ausente: " + str(path))
        if path.suffix.lower() not in (".py", ".dll"):
            raise ValueError("Tipo não permitido na distribuição")
    return paths


def _include_minilzo(root, stage):
    third_party = stage / "third_party" / "minilzo"
    third_party.mkdir(parents=True, exist_ok=True)
    upstream = root / "third_party" / "minilzo"
    for name in ("minilzo.c", "minilzo.h", "lzoconf.h", "lzodefs.h"):
        shutil.copyfile(upstream / name, third_party / name)
    shutil.copyfile(upstream / "COPYING", third_party / "COPYING")


def build(output, format="auto", root=ROOT):
    root, output = Path(root).resolve(), Path(output).resolve()
    if format not in ("auto", "source", "exe"):
        raise ValueError("Formato de distribuição desconhecido")
    files = source_files(root)
    available = importlib.util.find_spec("PyInstaller") is not None
    actual_format = "exe" if format == "exe" or (format == "auto" and available) else "source"
    if actual_format == "exe" and not available:
        raise RuntimeError("PyInstaller não está instalado neste Python. Use --format source ou um ambiente local com PyInstaller.")
    output.mkdir(parents=True, exist_ok=True)
    name = "WildlandsHUD" if actual_format == "exe" else "WildlandsHUD-fontes"
    stage = output / name
    archive = output / (name + ".zip")
    if stage.exists() or archive.exists():
        raise FileExistsError("A saída já existe. Escolha outra pasta para preservar a distribuição anterior.")
    stage.mkdir()
    if actual_format == "exe":
        # Resolve paths locally. Include dynamically loaded patchers explicitly.
        hidden = [path.stem for path in files if path.name.startswith("phoenix_")]
        command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
                   "--name", "WildlandsHUD", "--distpath", str(stage),
                   "--workpath", str(output / "build"), "--specpath", str(output),
                   "--paths", str(root), "--add-binary", str(root / "minilzo.dll") + ";."]
        for module in hidden:
            command.extend(["--hidden-import", module])
        command.append(str(root / "portable_hud.py"))
        subprocess.run(command, cwd=root, check=True)
        source_directory = stage / "source"
        source_directory.mkdir()
        for path in files:
            shutil.copyfile(path, source_directory / path.name)
    else:
        for path in files:
            shutil.copyfile(path, stage / path.name)
        (stage / "Abrir_WildlandsHUD.cmd").write_text(LAUNCHER, encoding="ascii")
    (stage / "LEIA-ME.txt").write_text(README, encoding="utf-8-sig")
    for notice in ("LICENSE", "THIRD_PARTY_NOTICES.md", "DISCLAIMER.md"):
        shutil.copyfile(root / notice, stage / notice)
    for guide in ("README.md", "README.pt-BR.md"):
        if (root / guide).is_file():
            shutil.copyfile(root / guide, stage / guide)
    _include_minilzo(root, stage)
    if actual_format == "exe":
        notices = stage / "third_party" / "runtime_notices"
        notices.mkdir()
        python_notice = Path(sys.base_prefix) / "LICENSE.txt"
        if python_notice.is_file():
            shutil.copyfile(python_notice, notices / "Python-LICENSE.txt")
        for notice in (Path(sys.base_prefix) / "tcl").glob("*/license.terms"):
            shutil.copyfile(notice, notices / (notice.parent.name + "-license.terms"))
        distribution = importlib.metadata.distribution("pyinstaller")
        for notice in distribution.files or ():
            if str(notice).endswith("licenses/COPYING.txt"):
                shutil.copyfile(distribution.locate_file(notice), notices / "PyInstaller-COPYING.txt")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                if ".forge" in path.name.lower() or path.suffix.lower() in (".bin", ".png", ".json"):
                    raise ValueError("Arquivo não redistribuível detectado: " + str(path))
                zipped.write(path, Path(name) / path.relative_to(stage))
    print(f"Distribuição {actual_format}: {archive} ({archive.stat().st_size:,} bytes)")
    if actual_format == "source":
        print("Esta edição exige Python 64 bits com Tcl/Tk. Nenhum arquivo do jogo foi incluído.")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("auto", "source", "exe"), default="auto")
    parser.add_argument("--output", type=Path, default=ROOT / "dist_portable")
    args = parser.parse_args()
    build(args.output, args.format)
