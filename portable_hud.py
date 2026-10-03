# SPDX-License-Identifier: GPL-2.0-or-later
"""Small local HUD installer front end; the distribution contains no game data."""
from __future__ import annotations

import contextlib
import datetime
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import queue
import shutil
import sys
import threading
import uuid

APP_NAME = "Wildlands HUD"
APP_VERSION = "0.5.1"
ARCHIVES = ("DataPC_extra.forge", "DataPC_extra_patch_01.forge")
VARIANTS = {
    "v5": "V5 — manter aliado caído e interação; ocultar restante (experimental)",
    "v4": "V4 — ocultar inimigos e aliados normais; manter caídos (confirmado)",
    "v3": "V3 — ocultar somente inimigos (confirmado)",
}


def default_cache(game):
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".cache"))) / "WildlandsHUD"
    identity = hashlib.sha256(str(Path(game).resolve()).casefold().encode("utf8")).hexdigest()[:16]
    return base / identity


def validate_game(game, restoring=False):
    game = Path(game).expanduser().resolve()
    if not game.is_dir():
        raise ValueError("Selecione a pasta onde Ghost Recon Wildlands está instalado.")
    for name in ARCHIVES:
        if not (game / name).is_file() and not (restoring and (game / (name + ".phoenixhud.original")).is_file()):
            raise ValueError(f"O arquivo {name} não foi encontrado nessa pasta.")
    return game


def _write_receipt(path, game, package, variant):
    # This receipt contains paths only. The package manifest remains the hash authority.
    content = {"version": 1, "game": str(game), "package": str(package), "variant": variant}
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf8") as stream:
            json.dump(content, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _receipt_packages(cache, game):
    # A successful commit can precede updating active.json if the app is interrupted.
    for filename in ("pending.json", "active.json"):
        receipt = cache / filename
        if receipt.is_file():
            try:
                data = json.loads(receipt.read_text(encoding="utf8"))
                if data.get("version") == 1 and Path(data["game"]).resolve() == game:
                    yield Path(data["package"]).resolve()
            except (OSError, ValueError, KeyError, TypeError):
                continue


def _matching_previous(hud, game, candidates):
    """Select a manifest matching live/backups, including partial installations."""
    checked = set()
    for candidate in candidates:
        candidate = Path(candidate).resolve()
        if candidate in checked:
            continue
        checked.add(candidate)
        try:
            manifest = hud.load_manifest(candidate)
            compatible = True
            for row in manifest["archives"]:
                live = game / row["name"]
                backup = game / (row["name"] + hud.BACKUP_SUFFIX)
                if backup.is_file() and hud.sha256(backup) != row["original_sha256"]:
                    compatible = False
                    break
                if live.is_file():
                    if hud.sha256(live) not in (row["original_sha256"], row["patched_sha256"]):
                        compatible = False
                        break
                elif not backup.is_file():
                    compatible = False
                    break
            if compatible:
                return candidate
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None


def _check_space(game, cache):
    archive_bytes = sum((game / name).stat().st_size for name in ARCHIVES)
    reserve = 512 * 1024 * 1024
    # Preparation and installation each need an additional archive-sized copy.
    same_volume = os.stat(game).st_dev == os.stat(cache).st_dev
    required_cache = archive_bytes * (2 if same_volume else 1) + reserve
    if shutil.disk_usage(cache).free < required_cache:
        raise OSError("Espaço insuficiente para preparar e conferir as cópias. Libere cerca de 9 GB.")
    if not same_volume and shutil.disk_usage(game).free < archive_bytes + reserve:
        raise OSError("Espaço insuficiente no disco do jogo para instalar as cópias verificadas.")


def run_operation(action, game, *, cache=None, previous=None, variant="v5", emit=print):
    """Perform one explicitly requested operation through the existing safe backend.

    Dependency import is lazy, so opening the UI/building a source distribution
    does not require a completed V4 patch or access to any game archives.
    """
    if action not in ("install", "restore"):
        raise ValueError("Operação desconhecida.")
    if variant not in VARIANTS:
        raise ValueError("Versão desconhecida.")
    game = validate_game(game, restoring=action == "restore")
    hud = importlib.import_module("phoenix_hud")
    hud.require_game_closed()
    cache = Path(cache).resolve() if cache is not None else default_cache(game)
    if cache == game or game in cache.parents:
        raise ValueError("As cópias temporárias precisam ficar fora da pasta do jogo.")
    cache.mkdir(parents=True, exist_ok=True)
    candidates = ([Path(previous)] if previous else []) + list(_receipt_packages(cache, game))
    previous_package = _matching_previous(hud, game, candidates)
    has_originals = any((game / (name + hud.BACKUP_SUFFIX)).exists() for name in ARCHIVES)
    if action == "restore":
        if previous_package is None:
            raise ValueError("Não encontrei o registro dessa instalação. Selecione o manifesto do pacote usado anteriormente.")
        emit("Conferindo os backups e restaurando os arquivos originais…")
        hud.restore(game, previous_package)
        for receipt_name in ("active.json", "pending.json"):
            receipt = cache / receipt_name
            if receipt.exists():
                receipt.unlink()
        emit("Restauração concluída. Os arquivos originais foram conferidos.")
        return {"action": action, "game": str(game), "package": str(previous_package)}
    prepare = getattr(hud, "prepare_" + variant, None)
    if prepare is None:
        # Never silently apply V3 when the user selected the extra ally behavior.
        raise RuntimeError(f"Esta distribuição não inclui a {variant.upper()}. Use uma distribuição atualizada.")
    if has_originals and previous_package is None:
        raise ValueError("Há um backup de instalação anterior. Selecione o manifesto dela para preservar os originais e atualizar com segurança.")
    if any((game / (name + ".phoenixhud.pending")).exists() for name in ARCHIVES):
        # Never overwrite the recovery receipt for a prior interrupted copy.
        # The backend can clear fully verified staged files via Restore, and
        # deliberately preserves unknown or partial copies for manual recovery.
        raise ValueError("Há uma aplicação interrompida. Use Restaurar originais antes de aplicar novamente. Se a restauração recusar algum arquivo, preserve os backups e o registro para recuperação.")
    _check_space(game, cache)
    package = cache / "packages" / (variant + "-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    package.parent.mkdir(parents=True, exist_ok=True)
    emit("Preparando o mod a partir dos arquivos do seu próprio jogo. Isso pode levar alguns minutos…")
    prepare(game, package, previous=previous_package if has_originals else None)
    hud.load_manifest(package)  # Refuse incomplete preparation before any install call.
    _write_receipt(cache / "pending.json", game, package, variant)
    emit("Preparação verificada. Instalando e preservando os arquivos originais…")
    if has_originals:
        hud.upgrade(game, package, previous_package)
    else:
        hud.install(game, package)
    _write_receipt(cache / "active.json", game, package, variant)
    (cache / "pending.json").unlink()
    emit("Instalação concluída. O botão Restaurar originais desfaz esta instalação.")
    return {"action": action, "variant": variant, "game": str(game), "package": str(package)}


class _QueueWriter(io.TextIOBase):
    def __init__(self, events):
        self.events = events
        self.buffer = ""

    def write(self, text):
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip():
                self.events.put(("log", line))
        return len(text)

    def flush(self):
        if self.buffer.strip():
            self.events.put(("log", self.buffer))
            self.buffer = ""


def launch_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title(APP_NAME + " " + APP_VERSION)
    root.geometry("760x560")
    root.minsize(680, 500)
    panel = ttk.Frame(root, padding=20)
    panel.pack(fill="both", expand=True)
    ttk.Label(panel, text=APP_NAME, font=("Segoe UI", 20, "bold")).pack(anchor="w")
    ttk.Label(panel, text="O mod usa os arquivos do seu jogo e guarda os originais para restauração.",
              wraplength=700).pack(anchor="w", pady=(4, 16))
    ttk.Label(panel, text="Pasta do jogo").pack(anchor="w")
    directory = tk.StringVar()
    location = ttk.Frame(panel)
    location.pack(fill="x", pady=(4, 14))
    entry = ttk.Entry(location, textvariable=directory)
    entry.pack(side="left", fill="x", expand=True)
    browse = ttk.Button(location, text="Escolher…", command=lambda: directory.set(
        filedialog.askdirectory(title="Selecione a pasta Ghost Recon Wildlands", mustexist=True) or directory.get()))
    browse.pack(side="left", padx=(8, 0))
    ttk.Label(panel, text="O que ocultar").pack(anchor="w")
    choice = ttk.Combobox(panel, values=list(VARIANTS.values()), state="readonly")
    choice.current(0)
    choice.pack(fill="x", pady=(4, 10))
    previous = tk.StringVar()
    previous_label = tk.StringVar(value="Primeira instalação: não é necessário selecionar nada abaixo.")

    def choose_previous():
        filename = filedialog.askopenfilename(title="Selecione o manifest.json da instalação anterior",
                                             filetypes=[("Registro da instalação", "manifest.json")])
        if filename:
            previous.set(str(Path(filename).parent))
            previous_label.set("Registro anterior selecionado: " + str(Path(filename).parent))

    advanced = ttk.Button(panel, text="Já uso o mod: selecionar registro anterior…", command=choose_previous)
    advanced.pack(anchor="w")
    ttk.Label(panel, textvariable=previous_label, wraplength=690).pack(anchor="w", pady=(4, 10))
    actions = ttk.Frame(panel)
    actions.pack(fill="x")
    events = queue.Queue()
    busy = {"value": False}
    log = tk.Text(panel, height=10, wrap="word", state="disabled", font=("Segoe UI", 10))
    progress = ttk.Progressbar(panel, mode="indeterminate")
    status = tk.StringVar(value="Feche o jogo antes de aplicar ou restaurar. Reserve cerca de 9 GB livres.")

    def append_log(text):
        log.configure(state="normal")
        log.insert("end", text + "\n")
        log.see("end")
        log.configure(state="disabled")

    def start(action):
        if busy["value"]:
            return
        game = directory.get().strip()
        if not game:
            messagebox.showerror(APP_NAME, "Escolha a pasta do jogo.")
            return
        selected = list(VARIANTS)[choice.current()]
        explicit_previous = previous.get() or None
        busy["value"] = True
        for control in controls:
            control.configure(state="disabled")
        progress.start(12)
        status.set("Trabalhando… mantenha esta janela aberta.")

        def worker():
            stream = _QueueWriter(events)
            try:
                with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                    result = run_operation(action, game, previous=explicit_previous, variant=selected,
                                           emit=lambda text: events.put(("log", text)))
                stream.flush()
                events.put(("success", result))
            except BaseException as error:
                stream.flush()
                text = str(error)
                if isinstance(error, PermissionError):
                    text += "\nExecute o aplicativo como administrador para alterar a pasta do jogo."
                events.put(("error", text))

        threading.Thread(target=worker, name="hud-installer", daemon=False).start()

    apply_button = ttk.Button(actions, text="Aplicar mod", command=lambda: start("install"))
    apply_button.pack(side="left")
    restore_button = ttk.Button(actions, text="Restaurar originais", command=lambda: start("restore"))
    restore_button.pack(side="left", padx=(10, 0))
    controls = (apply_button, restore_button, browse, entry, advanced, choice)
    progress.pack(fill="x", pady=(12, 8))
    ttk.Label(panel, textvariable=status, wraplength=690).pack(anchor="w", pady=(0, 8))
    log.pack(fill="both", expand=True)

    def poll():
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == "log":
                    append_log(value)
                    status.set(value)
                else:
                    busy["value"] = False
                    progress.stop()
                    for control in controls:
                        control.configure(state="readonly" if control is choice else "normal")
                    if kind == "error":
                        status.set("A operação não foi concluída. Veja a mensagem abaixo.")
                        append_log("ERRO: " + value)
                        messagebox.showerror(APP_NAME, value)
                    else:
                        status.set("Concluído. Você já pode abrir o jogo.")
                        messagebox.showinfo(APP_NAME, "Operação concluída e arquivos conferidos.")
        except queue.Empty:
            pass
        root.after(150, poll)

    def close():
        if busy["value"]:
            messagebox.showinfo(APP_NAME, "Aguarde a operação terminar para manter seus arquivos protegidos.")
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.after(150, poll)
    root.mainloop()


def self_check(output):
    """Exercise frozen runtime dependencies without opening or changing a game."""
    import tkinter as tk
    from forge_io import LzoCodec
    from phoenix_friendly_patch import FRIENDLY_TARGETS, OOS_EDITS
    from phoenix_full_hud_patch import HUD_TARGETS
    hud = importlib.import_module("phoenix_hud")
    codec = LzoCodec()
    sample = bytes(range(256)) * 16
    if codec.decompress(codec.compress(sample), len(sample)) != sample:
        raise RuntimeError("Falha na verificação da biblioteca de compressão.")
    if not callable(hud.prepare_v4) or len(FRIENDLY_TARGETS) != 4 or len(OOS_EDITS) != 2:
        raise RuntimeError("Componentes da V4 incompletos.")
    if not callable(hud.prepare_v5) or len(HUD_TARGETS) != 516:
        raise RuntimeError("Componentes da V5 incompletos.")
    window = tk.Tk()
    window.withdraw()
    window.update_idletasks()
    window.destroy()
    Path(output).write_text(json.dumps({"ok": True, "app_version": APP_VERSION,
                                       "frozen": bool(getattr(sys, "frozen", False)),
                                       "lzo_roundtrip": True, "tkinter": True,
                                       "v4_downed_offscreen_condition": True,
                                       "v5_full_hud_targets": len(HUD_TARGETS)}), encoding="utf8")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-check":
        self_check(sys.argv[2])
    else:
        launch_gui()
