# Licença, origem e avisos

**Cannelia Capture 1.0.0** é distribuído sob a **GNU General Public License,
versão 2 ou, a seu critério, qualquer versão posterior** (`GPL-2.0-or-later`).
O texto integral da GPL v2 está em [LICENSE](LICENSE).
Esse texto não foi alterado. Não há licença MIT ou proprietária adicional.

## Código de origem

Este aplicativo deriva do `cinnamon-screenshot`, parte de
[linuxmint/cinnamon](https://github.com/linuxmint/cinnamon), distribuído
sob GPL v2 ou posterior, conforme o README e os avisos do upstream.

- Revisão-base: [`d67b361f90bccc3346fe342b2a571b68ec1eb671`](https://github.com/linuxmint/cinnamon/tree/d67b361f90bccc3346fe342b2a571b68ec1eb671).
- Diretório original: `files/usr/share/cinnamon/cinnamon-screenshot`.
- Configurações originais: seção `org.cinnamon.screenshot` de `data/org.cinnamon.gschema.xml`.
- Contrato D-Bus: `ScreenshotIface` de `js/ui/screenshot.js`.
- Autores identificados no histórico do aplicativo: **Michael Webster** e **Cobinja**, além dos colaboradores do projeto Linux Mint/Cinnamon.

Uma cópia do aviso de copyright de empacotamento do upstream é preservada em
[upstream/cinnamon-copyright](upstream/cinnamon-copyright), para referência de
proveniência. Ela descreve também componentes do desktop que não são
redistribuídos neste repositório. Os copyrights do upstream permanecem com
seus respectivos titulares; Cannelia Capture não reivindica autoria exclusiva.

Os arquivos Python, a interface e os ícones herdados mantêm suas origens no
Cinnamon. Os arquivos modificados são identificados por avisos com a data
**28 de outubro de 2026** e pela documentação de alterações. O snapshot XML
em `upstream/org.cinnamon.Screenshot.xml` foi extraído do contrato upstream
para testar a compatibilidade; não implementa nem substitui o compositor.

## Alterações e código novo

Copyright © 2026 **yuri-schmaltz**, pelas alterações e pelos novos componentes
do Cannelia Capture. Esses componentes também usam GPL-2.0-or-later.
Veja [docs/CHANGES.md](docs/CHANGES.md) para uma descrição das modificações e
[AUTHORS.md](AUTHORS.md) para os créditos.

Os ícones incluídos neste repositório são derivados dos ícones distribuídos
com o aplicativo Cinnamon e seguem a licença do código de origem. O ícone `packaging/cannelia-capture.svg` é original de yuri-schmaltz (2026),
sob GPL-2.0-or-later, e acompanha o pacote Debian. O tema e
o ícone `applets-screenshooter` utilizados em tempo de execução pertencem
à instalação do usuário e não são copiados pelo instalador.

Python, GTK, PyGObject, Cairo e XApp são dependências externas instaladas
pelos repositórios da distribuição; não são incorporadas a este repositório.
Cada dependência mantém sua própria licença. Imagens de documentação mostram
o aplicativo com conteúdo sintético, sem capturas do desktop do usuário.

## Redistribuição e garantia

Ao redistribuir, preserve os créditos e avisos, disponibilize o código-fonte
correspondente às modificações e inclua a licença, conforme seus termos.
Este resumo não altera a licença. O programa é fornecido **sem qualquer
garantia**, inclusive de adequação a uma finalidade específica, nos termos
das seções 11 e 12 da GPL v2.

Referências: [GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
e [FAQ da GNU](https://www.gnu.org/licenses/gpl-faq.html).

Cannelia Capture não é um produto oficial nem representa uma afiliação com
o Linux Mint, GNOME ou os responsáveis pelas dependências.
