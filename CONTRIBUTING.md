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

Para testar sem a sessão do Cinnamon, instale também `xvfb`, `xauth` e
`dbus-x11`, e execute:

```bash
dbus-run-session -- xvfb-run -a /usr/bin/python3 tests/test-screenshot-local.py
```

Isso valida a GUI e as simulações de serviço, mas não comprova captura real
em um compositor. Para validar a integração real, rode o app em Cinnamon e
teste tela, região, janela, flash, temporizador, salvamento e cópia.

## Estrutura

| Caminho | Função |
| --- | --- |
| `files/usr/share/cinnamon/cinnamon-screenshot/` | Python, UI GTK, ícones, traduções e backends |
| `data/org.cinnamon.gschema.xml` | Somente as configurações do aplicativo |
| `run-screenshot.py` | Preparação/cache e execução local |
| `install-screenshot.py` | Instalação por usuário, atalhos, remoção |
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

## Publicação pelo mantenedor

Os metadados da seção About do GitHub estão em `.github/repository.json`.
Para revisar o alvo público, descrição, homepage e tópicos sem alterações remotas:

```bash
/usr/bin/python3 tools/publish-github.py --dry-run
```

Após os testes e um commit na branch `main`, autentique o GitHub CLI como
`yuri-schmaltz` e publique:

```bash
gh auth login --hostname github.com --git-protocol https --web
/usr/bin/python3 tools/publish-github.py
```

O script verifica o perfil, o remoto e o estado do checkout, cria o
repositório público quando necessário, faz push sem force e configura o About.
Nenhum token deve ser inserido no código, em arquivos versionados ou nos logs.
O arquivo LICENSE permite ao GitHub identificar a licença; NOTICE.md registra
explicitamente a opção GPL v2 **ou posterior** e os direitos dos autores originais.
