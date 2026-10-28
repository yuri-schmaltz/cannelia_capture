# Contribuir

O foco é um aplicativo de captura independente para o Cinnamon. Preserve
os créditos do upstream e use GPL-2.0-or-later para contribuições incluídas
no programa. A origem dos componentes está em NOTICE.md.

## Desenvolvimento

Instale as dependências descritas no README e execute pelo clone:

```bash
./run-screenshot.py --interactive
./run-screenshot.py --check
/usr/bin/python3 tests/test-screenshot-local.py
```

Use o Python do sistema. As preferências/cache de desenvolvimento ficam em
`.local-screenshot/`, separadas da instalação do usuário. A suíte usa imagens
sintéticas e um diretório de runtime temporário; não captura seu desktop.

Para testar sem a sessão do Cinnamon, instale também `xvfb`, `xauth`,
`dbus-x11`, `cinnamon-desktop-data`, `librsvg2-common`, `shared-mime-info` e
`at-spi2-core`. O pacote de dados fornece os schemas reais de atalhos usados
pelos testes; não inicia nem substitui o desktop. Execute:

```bash
dbus-run-session -- xvfb-run -a /usr/bin/python3 tests/test-screenshot-local.py
```

Isso valida a GUI e as simulações de serviço, mas não comprova captura real
em um compositor. Para validar a integração real, rode o app em Cinnamon e
teste tela, região, janela, flash, temporizador, salvamento e cópia.

## Execução e recursos

`run-screenshot.py` adiciona `src/cannelia_capture/` ao caminho de módulos.
Os módulos usam imports locais; o diretório não exige instalação via pip.
Schemas e traduções são compilados sob demanda em `.local-screenshot/`,
com bloqueio para impedir compilações concorrentes. `--help` e `--version`
funcionam sem carregar GTK nem criar estado do usuário.

No pacote Debian, esses recursos já estão compilados em
`/usr/share/cannelia-capture/`; o runtime não altera os arquivos do pacote.
Os IDs internos e os caminhos das preferências instaladas são preservados
para manter compatibilidade com instalações anteriores.

## Estrutura

| Caminho | Função |
| --- | --- |
| `src/cannelia_capture/` | Python, UI GTK, ícones, traduções e backends |
| `data/org.cinnamon.gschema.xml` | Somente as configurações do aplicativo |
| `run-screenshot.py` | Preparação/cache e execução local |
| `install-screenshot.py` | Instalação por usuário, atalhos, remoção |
| `packaging/` | Metadados Debian, ícone e página de manual |
| `tools/build-deb.py` | Construção reproduzível do pacote |
| `tests/test-deb.py` | Integração e reprodutibilidade do pacote |
| `tests/test-screenshot-local.py` | Testes de regressão com imagens sintéticas |
| `tools/benchmark-screenshot.py` | Medições usando o serviço real |
| `upstream/org.cinnamon.Screenshot.xml` | Snapshot do contrato D-Bus de referência |

## Validação de mudanças

- Execute os testes e `git diff --check`.
- Para UI, confira visualmente a tela inicial, preview, zoom, preferências e Sobre.
- Para salvamento, mantenha o arquivo anterior intacto quando houver erro.
- Para concorrência, teste processos distintos e cancelamento do seletor.
- Verifique os textos em pt-BR e inglês; atualize `po/pt_BR.po` junto com novos textos.
- Para instalar sem alterar seus atalhos, use um prefixo isolado:

```bash
./install-screenshot.py --prefix /tmp/cannelia-test --no-shortcuts
/tmp/cannelia-test/bin/cinnamon-screenshot-local --check
./install-screenshot.py --prefix /tmp/cannelia-test --uninstall
```

Não inclua caches, preferências pessoais, capturas do desktop, PATs ou
outros segredos nos commits. Screenshots de documentação devem usar conteúdo
sintético ou material que possa ser redistribuído.

Explique no pull request o problema concreto, a alteração, as verificações
realizadas e os limites relevantes. O aplicativo ainda precisa de testes
funcionais em Cinnamon recente e Wayland; não declare esse suporte como
validado apenas porque um teste de contrato ou uma simulação passou.

## Empacotamento e release

O repositório já está publicado em `yuri-schmaltz/cannelia-capture`.
A versão do produto é definida em `src/cannelia_capture/branding.py`;
o empacotador e o diálogo Sobre usam esse valor. Ao preparar uma versão,
atualize também o changelog, o catálogo pt-BR e as referências de instalação.

```bash
/usr/bin/python3 tools/build-deb.py
/usr/bin/python3 tests/test-deb.py
```

O teste do pacote verifica versão, arquitetura, Lintian, builds reproduzíveis,
recursos compilados e execução extraída sem modificar `/usr`.
Depois dos testes, envie o commit, aguarde o CI, crie a tag correspondente e
publique o `.deb` de `dist/` e o arquivo `SHA256SUMS` em uma release do GitHub.
Não sobrescreva os arquivos de uma release publicada com um build diferente;
correções posteriores devem receber uma nova versão.

O arquivo LICENSE permite ao GitHub identificar a licença; NOTICE.md registra
explicitamente a opção GPL v2 **ou posterior** e os direitos dos autores originais.
