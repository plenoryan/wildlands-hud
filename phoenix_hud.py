# SPDX-License-Identifier: GPL-2.0-or-later
"""Prepare, verify, install and restore the experimental enemy-only Phoenix HUD patch."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from forge_io import ForgeArchive, LzoCodec, decode_payload, encode_payload
from phoenix_patch import TARGETS, hide_container

ROOT = Path(__file__).resolve().parent
DEFAULT_GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Wildlands")
LEGACY_PACKAGE = ROOT / "prepared_phoenix"
PREVIOUS_PACKAGE = ROOT / "prepared_phoenix_v4"
DEFAULT_PACKAGE = ROOT / "prepared_phoenix_custom"
ARCHIVES = ("DataPC_extra.forge", "DataPC_extra_patch_01.forge")
BACKUP_SUFFIX = ".phoenixhud.original"
PENDING_SUFFIX = ".phoenixhud.pending"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_game_closed():
    if os.name != "nt":
        return
    result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
                            text=True, errors="replace", check=True,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    for line in result.stdout.splitlines():
        name = line.split(",", 1)[0].strip('"').lower()
        if name in ("grw.exe", "grw_plus.exe"):
            raise RuntimeError("Feche Ghost Recon Wildlands antes de continuar.")


def verify_rebuild(source, rebuilt, expected, codec, patcher=hide_container):
    """Compare every untouched entry, including every ally and revival resource."""
    changed = []
    if len(source.entries) != len(rebuilt.entries):
        raise ValueError("O numero de recursos mudou.")
    with source.path.open("rb") as original, rebuilt.path.open("rb") as output:
        for before, after in zip(source.entries, rebuilt.entries):
            if (before.file_id, before.name) != (after.file_id, after.name):
                raise ValueError("A identidade ou a ordem dos recursos mudou.")
            original.seek(before.offset)
            output.seek(after.offset)
            if before.file_id in expected:
                old = decode_payload(original.read(before.size), codec)
                new = decode_payload(output.read(after.size), codec)
                target = expected[before.file_id]
                if len(old.sets) != 2 or len(new.sets) != 2:
                    raise ValueError("Quantidade inesperada de conjuntos.")
                if old.sets[0] != new.sets[0] or old.trailer != new.trailer:
                    raise ValueError("Cabecalho ou rodape de recurso alterado.")
                if new.sets[1].data != patcher(old.sets[1].data, target):
                    raise ValueError("Alteracao Phoenix diferente da planejada.")
                if old.sets[1].header != new.sets[1].header:
                    raise ValueError("Cabecalho de compressao alterado.")
                changed.append(target.name)
            else:
                if before.size != after.size:
                    raise ValueError(f"Tamanho inesperado: {before.name}")
                remaining = before.size
                while remaining:
                    size = min(1024 * 1024, remaining)
                    a, b = original.read(size), output.read(size)
                    if len(a) != size or a != b:
                        raise ValueError(f"Recurso nao autorizado mudou: {before.name}")
                    remaining -= size
    if set(changed) != {t.name for t in expected.values()}:
        raise ValueError("Nem todas as alteracoes foram verificadas.")
    return len(source.entries) - len(changed)


def prepare(game, package, targets=TARGETS, patcher=hide_container, source_suffix="",
            variant=None, describe_change=None):
    # Frozen backup sources can be inspected while the game runs. The live-file
    # preparation path and every installation/restoration still require closure.
    if not source_suffix:
        require_game_closed()
    if game == package:
        raise ValueError("A pasta de preparo precisa ser separada da pasta do jogo.")
    if package.exists():
        raise FileExistsError(f"Pasta de preparo ja existe: {package}")
    codec = LzoCodec()
    plan = []
    # Validate both archives before creating any output.
    for name in ARCHIVES:
        archive = ForgeArchive(game / (name + source_suffix))
        replacements, expected = {}, {}
        for target in (t for t in targets if t.archive == name):
            entries = archive.find(target.name)
            if len(entries) != 1:
                raise ValueError(f"Recurso ausente ou ambiguo: {target.name}")
            entry = entries[0]
            payload = decode_payload(archive.read_raw(entry), codec)
            if len(payload.sets) != 2:
                raise ValueError(f"Estrutura inesperada: {target.name}")
            replacements[entry.file_id] = encode_payload(
                payload, {1: patcher(payload.sets[1].data, target)}, codec)
            expected[entry.file_id] = target
        plan.append((name, archive, replacements, expected, sha256(archive.path)))
    package.mkdir(parents=True)
    manifest = {"version": 1, "experimental": True, "game_directory": str(game), "archives": []}
    manifest["variant"] = variant or ("leaf-scale" if patcher is not hide_container else "wrapper-alpha")
    if describe_change is None:
        def describe_change(target):
            if patcher is hide_container:
                return {"alpha_offset": target.alpha_offset, "from": 1.0, "to": 0.0}
            return {"visual_instances": target.node_count, "scale_xy_to": [0.0, 0.0]}
    for name, archive, replacements, expected, source_hash in plan:
        print(f"Preparando e conferindo {name}...", flush=True)
        archive.rebuild(package / name, replacements)
        rebuilt = ForgeArchive(package / name)
        untouched = verify_rebuild(archive, rebuilt, expected, codec, patcher)
        if sha256(archive.path) != source_hash:
            raise ValueError("O arquivo de origem mudou durante o preparo.")
        manifest["archives"].append({
            "name": name, "original_sha256": source_hash,
            "patched_sha256": sha256(package / name),
            "unchanged_entries_verified": untouched,
            "changes": [{"name": t.name, "file_id": fid, **describe_change(t)}
                        for fid, t in expected.items()],
        })
        print(f"  {len(expected)} recursos alterados; {untouched} recursos identicos.", flush=True)
    (package / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Pacote conferido. O jogo ainda nao foi alterado. E necessario testar o resultado em jogo.")


def load_manifest(package):
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("version") != 1 or [r["name"] for r in manifest["archives"]] != list(ARCHIVES):
        raise ValueError("Manifesto desconhecido.")
    return manifest


def prepare_v2(game, package, previous):
    from phoenix_leaf_patch import TARGETS as leaf_targets, hide_visuals
    old = load_manifest(previous)
    for row in old["archives"]:
        if sha256(game / (row["name"] + BACKUP_SUFFIX)) != row["original_sha256"]:
            raise ValueError("O backup anterior ao primeiro teste nao confere.")
    prepare(game, package, leaf_targets, hide_visuals, BACKUP_SUFFIX)


def prepare_v3(game, package, previous=None):
    from phoenix_image_patch import TARGETS as image_targets, hide_enemy_visuals
    from phoenix_image_patch import change_details, verify_image_provider
    suffix = ""
    if previous is not None:
        old = load_manifest(previous)
        for row in old["archives"]:
            if sha256(game / (row["name"] + BACKUP_SUFFIX)) != row["original_sha256"]:
                raise ValueError("O backup anterior aos testes nao confere.")
        suffix = BACKUP_SUFFIX
    verify_image_provider(ForgeArchive(game / (ARCHIVES[0] + suffix)), LzoCodec())
    prepare(game, package, image_targets, hide_enemy_visuals, suffix,
            variant="leaf-scale-transparent-image", describe_change=change_details)


def prepare_v4(game, package, previous=None):
    from phoenix_friendly_patch import TARGETS as v4_targets, hide_markers_except_downed, change_details
    from phoenix_friendly_patch import verify_downed_gauge
    from phoenix_image_patch import verify_image_provider
    suffix = ""
    if previous is not None:
        old = load_manifest(previous)
        for row in old["archives"]:
            if sha256(game / (row["name"] + BACKUP_SUFFIX)) != row["original_sha256"]:
                raise ValueError("O backup anterior aos testes nao confere.")
        suffix = BACKUP_SUFFIX
    verify_image_provider(ForgeArchive(game / (ARCHIVES[0] + suffix)), LzoCodec())
    for archive_name in ARCHIVES:
        verify_downed_gauge(ForgeArchive(game / (archive_name + suffix)), archive_name, LzoCodec())
    prepare(game, package, v4_targets, hide_markers_except_downed, suffix,
            variant="enemy-and-normal-ally-hidden-downed-preserved", describe_change=change_details)


def prepare_v5(game, package, previous=None):
    from phoenix_full_hud_patch import TARGETS as v5_targets, hide_hud_except_downed, change_details
    from phoenix_friendly_patch import verify_downed_gauge
    from phoenix_image_patch import verify_image_provider
    suffix = ""
    if previous is not None:
        old = load_manifest(previous)
        for row in old["archives"]:
            if sha256(game / (row["name"] + BACKUP_SUFFIX)) != row["original_sha256"]:
                raise ValueError("O backup anterior aos testes nao confere.")
        suffix = BACKUP_SUFFIX
    codec = LzoCodec()
    verify_image_provider(ForgeArchive(game / (ARCHIVES[0] + suffix)), codec)
    for archive_name in ARCHIVES:
        verify_downed_gauge(ForgeArchive(game / (archive_name + suffix)), archive_name, codec)
    prepare(game, package, v5_targets, hide_hud_except_downed, suffix,
            variant="full-hud-hidden-downed-preserved", describe_change=change_details)


def prepare_custom(game, package, previous=None, options=None):
    from phoenix_options import normalize_options, selected_targets, patch_selected, describe_change, verify_invisible
    from phoenix_friendly_patch import verify_downed_gauge
    options = normalize_options(options)
    suffix = ''
    if previous is not None:
        for row in load_manifest(previous)['archives']:
            if sha256(game / (row['name'] + BACKUP_SUFFIX)) != row['original_sha256']:
                raise ValueError('O backup anterior aos testes nao confere.')
        suffix = BACKUP_SUFFIX
    codec = LzoCodec()
    for name in ARCHIVES:
        archive = ForgeArchive(game / (name + suffix))
        verify_invisible(archive, name, codec)
        verify_downed_gauge(archive, name, codec)
    prepare(game, package, selected_targets(options), patch_selected, suffix,
            variant='custom', describe_change=describe_change)
    manifest = load_manifest(package)
    manifest['options'] = options
    (package / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def upgrade(game, package, previous):
    """Validate a replacement package, restore backups, then use the installer.

    If installation fails, the installer's rollback leaves original game files.
    Prepared previous packages remain available for an explicit reinstall.
    """
    require_game_closed()
    old, new = load_manifest(previous), load_manifest(package)
    for a, b in zip(old["archives"], new["archives"]):
        if a["original_sha256"] != b["original_sha256"]:
            raise ValueError("Os pacotes nao partem dos mesmos arquivos originais.")
        if sha256(package / b["name"]) != b["patched_sha256"]:
            raise ValueError("Pacote novo alterado; atualizacao cancelada.")
    restore(game, previous)
    install(game, package)


def install(game, package):
    require_game_closed()
    manifest = load_manifest(package)
    rows = manifest["archives"]
    for row in rows:
        live = game / row["name"]
        backup = game / (row["name"] + BACKUP_SUFFIX)
        pending = game / (row["name"] + PENDING_SUFFIX)
        if backup.exists() or pending.exists():
            raise FileExistsError(f"Backup ou preparo anterior encontrado. Restaure antes de instalar: {live.name}")
        if sha256(live) != row["original_sha256"]:
            raise ValueError(f"O jogo mudou desde o preparo: {live.name}. Prepare um novo pacote.")
        if sha256(package / live.name) != row["patched_sha256"]:
            raise ValueError(f"Pacote alterado: {live.name}")
    staged = []
    backed_up = []
    try:
        # All copies finish and pass SHA256 before the first live file is changed.
        for row in rows:
            pending = game / (row["name"] + PENDING_SUFFIX)
            with (package / row["name"]).open("rb") as source, pending.open("xb") as output:
                staged.append(pending)
                shutil.copyfileobj(source, output, 8 * 1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
            if sha256(pending) != row["patched_sha256"]:
                raise ValueError("Falha na verificacao da copia de instalacao.")
        require_game_closed()
        for row in rows:
            live = game / row["name"]
            if sha256(live) != row["original_sha256"]:
                raise ValueError("O jogo mudou durante a instalacao.")
        for row in rows:
            live = game / row["name"]
            backup = game / (row["name"] + BACKUP_SUFFIX)
            live.rename(backup)  # Windows refuses to replace an existing backup.
            backed_up.append((live, backup))
            os.replace(game / (row["name"] + PENDING_SUFFIX), live)
        for row in rows:
            if sha256(game / row["name"]) != row["patched_sha256"]:
                raise ValueError("Falha na verificacao final da instalacao.")
    except BaseException:
        for live, backup in reversed(backed_up):
            if backup.exists():
                os.replace(backup, live)
        raise
    finally:
        for pending in staged:
            if pending.exists():
                pending.unlink()
    print("Teste Phoenix instalado. Os originais foram preservados para restauracao.")
    print("Validacao visual pendente: inimigos sem icones/metros/pulso e aliados caidos visiveis.")


def restore(game, package):
    require_game_closed()
    manifest = load_manifest(package)
    pending_restores = []
    verified_pending = []
    # Accept an interrupted installation: the live file may be absent.
    for row in manifest["archives"]:
        live = game / row["name"]
        backup = game / (row["name"] + BACKUP_SUFFIX)
        pending = game / (row["name"] + PENDING_SUFFIX)
        if pending.exists():
            if sha256(pending) != row["patched_sha256"]:
                raise ValueError(f"Preparo interrompido com conteudo desconhecido: {pending.name}")
            verified_pending.append(pending)
        if not backup.exists():
            if live.exists() and sha256(live) == row["original_sha256"]:
                continue
            raise ValueError(f"Backup ausente e estado desconhecido: {live.name}")
        if sha256(backup) != row["original_sha256"]:
            raise ValueError(f"Backup diferente do original: {backup.name}")
        if live.exists() and sha256(live) not in (row["patched_sha256"], row["original_sha256"]):
            raise ValueError(f"O arquivo foi alterado depois do teste: {live.name}. Restauracao cancelada.")
        pending_restores.append((live, backup, row))
    for live, backup, row in pending_restores:
        os.replace(backup, live)
        if sha256(live) != row["original_sha256"]:
            raise ValueError(f"Falha ao verificar restauracao: {live.name}")
    for pending in verified_pending:
        pending.unlink()
    print("Arquivos originais restaurados e conferidos.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "prepare-v2", "prepare-v3", "prepare-v4", "prepare-v5", "upgrade", "install", "restore", "status"))
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--package", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--previous-package", type=Path, default=PREVIOUS_PACKAGE)
    args = parser.parse_args()
    game, package = args.game_dir.resolve(), args.package.resolve()
    if args.action in ("prepare-v2", "prepare-v3", "prepare-v4", "prepare-v5", "upgrade"):
        {"prepare-v2": prepare_v2, "prepare-v3": prepare_v3, "prepare-v4": prepare_v4, "prepare-v5": prepare_v5, "upgrade": upgrade}[args.action](
            game, package, args.previous_package.resolve())
    elif args.action == "status":
        manifest = load_manifest(package)
        for row in manifest["archives"]:
            live = game / row["name"]
            current = sha256(live) if live.exists() else None
            state = "experimental instalado" if current == row["patched_sha256"] else (
                "original" if current == row["original_sha256"] else "estado diferente/ausente")
            print(f"{row['name']}: {state}")
    elif args.action == "prepare":
        prepare_custom(game, package)
    else:
        {"install": install, "restore": restore}[args.action](game, package)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)
