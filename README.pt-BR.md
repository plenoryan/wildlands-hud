# Wildlands HUD

Escolha o que ocultar com caixas de seleção. **Marcado = ocultar; desmarcado = manter.** O seletor de versões foi removido. Aliado caído e avisos de interação são sempre preservados.

[Download v0.6.0](https://github.com/plenoryan/wildlands-hud/releases/download/v0.6.0/WildlandsHUD.zip) · [Website](https://plenoryan.github.io/wildlands-hud/) · [Changelog](CHANGELOG.md)

## Seleção padrão

| Opção | Padrão |
| --- | --- |
| Inimigos: ícones, nomes, distâncias e pulsos | Ocultar |
| Objetos: geradores, alarmes, minas e afins | Ocultar |
| Aliados normais: ícones, nomes e distâncias | Ocultar |
| Outros marcadores: objetivos, coleta, pings e tiro sincronizado | Ocultar |
| Minimapa | Manter |
| Mira | Manter |
| Informações do binóculo e drone | Manter |
| Informações de armas e munição | Manter |

A opção de objetos também inclui minas próprias e outros objetos agrupados pelo jogo. Não há uma caixa separada para cada equipamento. Binóculo e drone ficam na mesma opção porque compartilham elementos. Outros marcadores inclui objetivos e coleta; desmarque para mantê-los.

## Aplicar e atualizar

1. Extraia o ZIP e feche o jogo.
2. Execute `WildlandsHUD.exe` e selecione sua pasta do jogo. Se faltar permissão, execute como administrador.
3. Revise as caixas e clique em **Aplicar mod**. **Voltar à seleção padrão** apenas redefine as caixas; clique em Aplicar para gravar.
4. Para atualizar de V3/V4/V5 ou alterar as escolhas, aplique novamente. O instalador usa os backups originais e guarda as opções no manifesto. Se solicitado, indique o manifesto anterior em **Já uso o mod**.

**Restaurar originais** devolve a interface original. Mantenha os arquivos `.phoenixhud.original` junto ao jogo e os registros em `%LOCALAPPDATA%\WildlandsHUD` enquanto o mod estiver instalado. Versões desconhecidas ou arquivos alterados por outros programas são recusados.

## Validação e limites

- Windows 64 bits, instalação própria do jogo e cerca de 9 GB livres. O executável inclui Python; não exige instalação separada.
- A seleção padrão preserva binóculo, drone, mira, minimapa, munição e interação. Com aliados normais ocultos, os nomes/distâncias dos caídos também ficam ocultos; o símbolo/medidor e as setas condicionais permanecem.
- A edição configurável é experimental e ainda precisa de confirmação em partida. Testes de arquivos não comprovam todos os estados visuais do jogo.
- As imagens ocultas usam um recurso transparente que já existe no jogo. Nenhuma textura compartilhada é modificada pela edição configurável.
- O ZIP não contém arquivos do jogo, texturas, recursos extraídos ou saves. Cada pessoa prepara a partir de sua própria instalação.

## Development

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -v
python portable_hud.py --self-check self_check.json
python build_portable.py --format exe --output dist_custom
```

Private game fixtures are not distributed; tests requiring them skip in public CI.

[Isenção de responsabilidade](DISCLAIMER.md) · [GPL-2.0-or-later](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)
