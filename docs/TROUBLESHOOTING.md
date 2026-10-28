# Solução de problemas

## O app não abre

Execute pelo terminal e verifique o diagnóstico:

```bash
~/.local/bin/cinnamon-screenshot-local --check
~/.local/bin/cinnamon-screenshot-local --interactive
```

Use `/usr/bin/python3` e instale as dependências do README. Um Python de
ambiente virtual pode não enxergar `gi`, GTK ou XApp. O aplicativo requer
uma sessão gráfica; ele não captura uma sessão remota/headless por conta própria.

## Região, janela ou sombras indisponíveis

`--check` informa o backend e a presença do serviço. No Cinnamon 6.6,
`LegacyBackend` é esperado. A seleção de região depende do serviço do
Cinnamon. Capturar a janela ativa funciona na interface antiga, mas
selecioná-la por clique e controlar sombras exigem o serviço novo.
Não instale um Cinnamon de desenvolvimento apenas para executar o app.

## Os atalhos não respondem

Confira **Configurações do Sistema → Teclado → Atalhos personalizados**.
Os comandos devem apontar para `~/.local/bin/cinnamon-screenshot-local`
com `--area` ou `--window` conforme a ação. O caminho é expandido pelo
instalador. Confira conflitos com outros gerenciadores de atalhos ou apps.
Os dois Shifts são equivalentes para o Cinnamon.

Se instalou com `--no-shortcuts`, configure manualmente ou execute o
instalador novamente sem esse argumento. O instalador não remove atalhos
alheios para resolver um conflito.

## A imagem não apareceu na pasta esperada

Confira o destino nas Preferências e se o salvamento automático está ativo.
Uma pasta removida, um volume desmontado ou falta de permissão gera erro.
O app não salva em outra pasta silenciosamente. No editor, Salvar permite
escolher outro destino mesmo quando a pasta padrão ficou indisponível.

## O arquivo foi salvo, mas não foi copiado

No Cinnamon 6.6, a cópia depende do GTK e do gerenciador da área de
transferência da sessão. A mensagem distingue a falha de cópia da gravação.
Teste colar em um editor de imagens e veja se um gerenciador de clipboard
está interceptando ou descartando imagens. O arquivo salvo permanece válido.

## O flash não aparece

Ative **Preferências → Comportamento → Usar flash**. O backend antigo envia
essa preferência ao serviço. O fallback X11 não implementa o flash do
compositor; verifique o backend com `--check`.

## Uma nova captura informa que já há outra em andamento

Termine ou cancele o seletor anterior com Esc. Capturas com temporizador
também ocupam o bloqueio até terminar. Fechar o processo libera o bloqueio
do kernel; a mera presença do arquivo `capture.lock` não significa que o
app continua ocupado. Não é preciso apagar esse arquivo.

## Quero restaurar os padrões

Feche o app e faça uma cópia de segurança das preferências antes de alterar:

```bash
cp -a ~/.config/cinnamon-screenshot-local ~/.config/cinnamon-screenshot-local.backup
```

As configurações estão no arquivo
`~/.config/cinnamon-screenshot-local/glib-2.0/settings/keyfile`. Remover esse
arquivo faz o próximo início recriar as preferências padrão. Essa ação
perde suas opções personalizadas e não apaga as imagens.

## Reportar um problema

Abra uma issue com a versão do Cannelia Capture, Mint/Cinnamon, tipo de
sessão (X11/Wayland), saída de `--check`, passos e erro observado. Remova
informações pessoais de logs/imagens antes de anexá-los. Não publique PATs,
credenciais, capturas privadas ou arquivos de preferências completos.
