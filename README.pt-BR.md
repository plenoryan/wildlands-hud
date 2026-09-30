# Wildlands HUD

**Instalador local de mod de HUD para Tom Clancy’s Ghost Recon Wildlands no Windows.** Oculte marcadores de inimigos ou experimente ocultar os marcadores normais de aliados, mantendo a indicação de aliado caído.

[English](README.md) · [Site do projeto](https://plenoryan.github.io/wildlands-hud/) · [Baixar v0.4.0](https://github.com/plenoryan/wildlands-hud/releases/download/v0.4.0/WildlandsHUD.zip) · [Notas da versão](CHANGELOG.md)

**A v0.4.0 é uma prévia experimental.** A V3 funcionou no teste em partida relatado. O comportamento adicional de aliados da V4 ainda precisa de confirmação dentro do jogo, incluindo aliados caídos fora da tela e o estado após a reanimação.

## Escolha uma opção

| Opção | Comportamento | Validação |
| --- | --- | --- |
| **V3 — somente inimigos** | Oculta os ícones, distâncias, círculos e pulsos dos inimigos nos alvos inspecionados. | Confirmada em um teste relatado dentro do jogo. |
| **V4 — inimigos e aliados normais** | Inclui a V3 e oculta marcadores normais, nomes e distâncias de aliados. Preserva o gauge/símbolo de aliado caído e condiciona as duas setas fora da tela ao aliado estar caído e fora da tela. | Recursos conferidos e testes automatizados; comportamento adicional dos aliados ainda sem confirmação em partida. |

A V4 também oculta nomes e distâncias de aliados enquanto estão caídos. O que permanece é o gauge/símbolo de caído e as setas condicionais fora da tela, não esses textos. O mod atua nos recursos de HUD inspecionados; não promete remover todas as categorias de marcador. Os marcadores de tiro sincronizado (Sync Shot) estão fora da lista de alvos.

## Instalação

É necessário **Windows de 64 bits**, uma instalação própria de Ghost Recon Wildlands e aproximadamente **9 GB livres** no primeiro preparo. O executável para download já inclui o runtime Python; você não precisa instalar Python.

1. [Baixe WildlandsHUD.zip](https://github.com/plenoryan/wildlands-hud/releases/download/v0.4.0/WildlandsHUD.zip) e extraia todo o conteúdo.
2. Feche Ghost Recon Wildlands.
3. Clique com o botão direito em `WildlandsHUD.exe` e escolha **Executar como administrador**.
4. Selecione a pasta de instalação do jogo.
5. Escolha **V3** ou **V4** e clique em **Aplicar mod**.
6. Aguarde o preparo, a conferência e a instalação terminarem antes de abrir o jogo.

Na V4, confira um aliado normal, um aliado caído dentro da tela, um aliado caído fora da tela e o estado após a reanimação. Relate o resultado em [Issues](https://github.com/plenoryan/wildlands-hud/issues).

O aplicativo prepara o mod usando os arquivos locais do seu jogo. O download contém código, executável e avisos/fontes das dependências; **não contém arquivos do jogo, recursos extraídos, texturas ou saves**. Cada pessoa precisa preparar o mod a partir da própria instalação.

## Restaurar o HUD original

Feche o jogo, abra o aplicativo, selecione a mesma pasta do jogo e clique em **Restaurar originais**.

Os arquivos originais ficam ao lado dos arquivos do jogo com o sufixo `.phoenixhud.original`. Os arquivos de preparo e os registros da instalação ficam em `%LOCALAPPDATA%\WildlandsHUD`. **Mantenha esses backups e registros enquanto o mod estiver instalado.** Se já usava um pacote anterior, selecione **Já uso o mod** e indique o `manifest.json` daquele pacote quando solicitado.

O aplicativo confere os hashes antes de instalar ou restaurar. Alterações desconhecidas são recusadas para preservar os arquivos. Se uma instalação interrompida não puder ser restaurada automaticamente, mantenha os backups e registros para recuperação; algumas interrupções podem exigir ajuda manual.

## Compatibilidade e limites

- A compatibilidade depende dos hashes dos recursos inspecionados, não de uma promessa de suporte a todas as versões ou lojas do jogo.
- Versões desconhecidas dos recursos são recusadas. Uma atualização do jogo ou outro mod que altere os mesmos arquivos pode exigir nova análise.
- O resultado em partida da V3 não valida todos os estados do jogo. As alterações de aliados da V4 ainda exigem teste em partida.
- Os testes automatizados verificam manipulação de arquivos, limites das alterações e comportamento do aplicativo. Eles não executam o jogo nem comprovam o resultado visual.

## Executar ou compilar a partir do código

O CI público usa **Python 3.11 de 64 bits no Windows**. Para executar o código, é necessário Python com Tcl/Tk e a `minilzo.dll` incluída.

```powershell
py -3.11 portable_hud.py
```

Para gerar o ZIP com executável, use uma pasta de saída nova:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python build_portable.py --format exe --output dist_release
```

O resultado fica em `dist_release\WildlandsHUD.zip`. O pacote inclui os fontes do aplicativo, a licença e os materiais de terceiros. Também é possível gerar um pacote somente com fontes usando `--format source`.

Para recompilar o miniLZO com GCC para Windows de 64 bits, execute na raiz do repositório:

```powershell
gcc -O2 -shared -static-libgcc third_party/minilzo/minilzo.c -o minilzo.dll
```

## Testes e contribuições

```powershell
.\.venv\Scripts\python -m unittest discover -v
.\.venv\Scripts\python portable_hud.py --self-check self-check.json
```

Os testes públicos usam dados sintéticos quando possível. Os testes que dependem de arquivos proprietários do jogo são ignorados quando esses arquivos não estão presentes; esses dados não são distribuídos. O CI também gera o executável e confere seu runtime sem abrir ou alterar uma instalação do jogo. Um CI aprovado não equivale à validação em partida.

Consulte [CONTRIBUTING.md](CONTRIBUTING.md) para conhecer as restrições das alterações e relatar problemas.

## Licença

Wildlands HUD é distribuído sob a **GNU GPL versão 2 ou posterior**; consulte [LICENSE](LICENSE). Os fontes e a licença do miniLZO estão em [third_party/minilzo](third_party/minilzo). Os componentes de runtime empacotados mantêm seus próprios avisos.

Este é um projeto independente da comunidade, sem vínculo oficial com a Ubisoft. Ghost Recon Wildlands e os arquivos do jogo pertencem aos respectivos titulares.
