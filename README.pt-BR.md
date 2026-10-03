# Wildlands HUD

**Correção 0.5.1:** mantém os avisos de interação e os botões de ação (como “aperte X”), além do aliado caído. O restante do HUD inspecionado continua oculto. Atualize usando o mesmo modo V5 e clique em **Aplicar mod**; o instalador reaplica a correção a partir dos originais. Confirmação em partida ainda pendente.

**V5 experimental — HUD oculto, exceto aliado caído e interação.** Novo modo padrão: oculta os recursos de HUD inspecionados, incluindo geradores e outros objetos, nomes/distâncias, mira, minimapa, munição e avisos. Preserva a lógica de caído da V4. Ainda não foi testado em partida; confira o caído dentro/fora da tela e após reanimação. Elementos gerados pelo jogo podem exigir ajustes. V3 e V4 continuam disponíveis.

**Instalador local de mod de HUD para Tom Clancy’s Ghost Recon Wildlands no Windows.** Oculte marcadores de inimigos ou experimente ocultar os marcadores normais de aliados, mantendo a indicação de aliado caído.

[English](README.md) · [Site do projeto](https://plenoryan.github.io/wildlands-hud/) · [Baixar v0.5.1](https://github.com/plenoryan/wildlands-hud/releases/download/v0.5.1/WildlandsHUD.zip) · [Notas da versão](CHANGELOG.md)

**V3 e V4 tiveram funcionamento confirmado em testes em partida relatados pelo criador.** A v0.4.0 continua sendo a primeira prévia pública; esses relatos não comprovam compatibilidade com todas as instalações, versões ou situações do jogo.

## Escolha uma opção

| Opção | Comportamento | Validação |
| --- | --- | --- |
| **V5 — HUD oculto** | Oculta o HUD inspecionado e mantém o indicador de aliado caído da V4. | Experimental; teste em partida pendente. |
| **V3 — somente inimigos** | Oculta os ícones, distâncias, círculos e pulsos dos inimigos nos alvos inspecionados. | Confirmada em um teste relatado dentro do jogo. |
| **V4 — inimigos e aliados normais** | Inclui a V3 e oculta marcadores normais, nomes e distâncias de aliados. Preserva o gauge/símbolo de aliado caído e condiciona as duas setas fora da tela ao aliado estar caído e fora da tela. | Recursos conferidos, testes automatizados e funcionamento confirmado em teste em partida relatado pelo criador. |

A V4 também oculta nomes e distâncias de aliados enquanto estão caídos. O que permanece é o gauge/símbolo de caído e as setas condicionais fora da tela, não esses textos. O mod atua nos recursos de HUD inspecionados; não promete remover todas as categorias de marcador. Na V3/V4, tiro sincronizado (Sync Shot) fica fora dos alvos; a V5 também inclui esse HUD.

## Instalação

É necessário **Windows de 64 bits**, uma instalação própria de Ghost Recon Wildlands e aproximadamente **9 GB livres** no primeiro preparo. O executável para download já inclui o runtime Python; você não precisa instalar Python.

1. [Baixe WildlandsHUD.zip](https://github.com/plenoryan/wildlands-hud/releases/download/v0.5.1/WildlandsHUD.zip) e extraia todo o conteúdo.
2. Feche Ghost Recon Wildlands.
3. Clique com o botão direito em `WildlandsHUD.exe` e escolha **Executar como administrador**.
4. Selecione a pasta de instalação do jogo.
5. Escolha **V5**, **V4** ou **V3** e clique em **Aplicar mod**.
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
- Os testes em partida relatados de V3 e V4 não validam todos os estados ou versões do jogo.
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

## Isenção de responsabilidade

Use o mod por sua conta e risco. Ele é fornecido **no estado em que se encontra, sem garantia**. Na medida permitida pela lei, o autor e os colaboradores não se responsabilizam por danos ou perdas decorrentes do uso, incluindo perda de arquivos/saves, falhas do jogo ou sanções de plataformas. Preserve seus backups e cumpra as regras do jogo e da plataforma. Consulte a [isenção completa](DISCLAIMER.md), que preserva os direitos legais obrigatórios e os termos da GPL.

## Licença

Wildlands HUD é distribuído sob a **GNU GPL versão 2 ou posterior**; consulte [LICENSE](LICENSE). Os fontes e a licença do miniLZO estão em [third_party/minilzo](third_party/minilzo). Os componentes de runtime empacotados mantêm seus próprios avisos.

Este é um projeto independente da comunidade, sem vínculo oficial com a Ubisoft. Ghost Recon Wildlands e os arquivos do jogo pertencem aos respectivos titulares.
