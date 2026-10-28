# Cannelia Capture — desenvolvimento local

Execute na raiz deste clone:

```sh
./run-screenshot.py --interactive
./run-screenshot.py --help
```

O lançador usa Python do sistema, GTK 3, PyGObject, XApp e
`glib-compile-schemas` e `msgfmt`. Não compila nem instala o desktop Cinnamon.
Recursos visuais são lidos do clone. O schema de captura é extraído do
schema oficial e compilado em `.local-screenshot/schemas`; preferências
ficam em `.local-screenshot/config`, usando o backend keyfile do GSettings.
Essa pasta é ignorada pelo Git. Nenhuma configuração do Cinnamon instalado
é substituída.

Schemas e traduções são compilados somente quando suas fontes mudam. A
preparação usa um bloqueio para evitar duas compilações concorrentes.
`--help` não carrega GTK nem conecta aos serviços de captura. Para conferir
dependências, recursos da interface e o backend ativo sem capturar:

```sh
./run-screenshot.py --check
```

No Cinnamon recente, a captura usa `org.cinnamon.Screenshot`. No Cinnamon
6.6, usa a interface antiga `org.gnome.Shell.Screenshot`: tela inteira,
janela ativa e seleção de região. Escolher uma janela clicando nela exige
o serviço novo; a interface local captura a janela ativa nessa versão.
Controle independente de sombras e cursor em regiões não estão disponíveis
na interface antiga. A cópia nesse modo é feita pelo GTK. O flash respeita
a preferência "Use a flash". Sem ambos os serviços, permanece a captura X11 limitada.

Testes de regressão:

```sh
/usr/bin/python3 tests/test-screenshot-local.py
```

Os testes usam imagens sintéticas e não capturam a tela.

## Interface e idioma

A tela inicial mostra os quatro modos e a ação Capturar, sem botão Fechar.
O temporizador (0 a 3600 segundos), a inclusão do ponteiro e a sombra da
janela ficam no menu → Preferências → Captura. Essas preferências são lidas
a cada captura, incluindo os atalhos; `--delay` pode substituir o temporizador.
Após a captura,
a janela cresce para exibir a prévia, Recortar, Desfazer, Copiar e Salvar.
O recorte tem oito alças de ajuste, pode ser movido arrastando seu interior
e mostra as dimensões em pixels. O zoom oferece Ajustar, 50%, 100%, 150%,
200% e 400%, com barras de rolagem. Seleção e dimensões permanecem em pixels
da imagem quando o zoom muda. Desfazer restaura a imagem anterior.
Com salvamento automático ativo, a captura feita pela interface também é
salva na pasta padrão; a prévia continua aberta para edição. A confirmação
mostra a pasta e oferece Abrir pasta. Recortar ou desfazer marca a imagem
como não salva. Uma captura por atalho continua sem abrir o editor e mostra
uma notificação com a ação Abrir pasta.

O Cinnamon possui tradução oficial em pt_BR. Textos novos deste aplicativo
são complementados por `files/usr/share/cinnamon/cinnamon-screenshot/po/pt_BR.po`.
O lançador compila esse catálogo em `.local-screenshot/locale` e usa o idioma
configurado no ambiente (`LANGUAGE`/`LANG`), com o catálogo do Cinnamon como
alternativa para textos já existentes. A interface e as preferências foram
verificadas em português brasileiro.

## Atalhos locais

Atalhos globais configurados no Cinnamon deste usuário:

| Captura | Atalho | Argumentos do lançador |
| --- | --- | --- |
| Desktop inteiro | Super + Shift + A | nenhum |
| Seleção | Super + Shift + S | `--area` |
| Janela atual | Super + Shift + D | `--window` |

Após a instalação, as entradas apontam para
`~/.local/bin/cinnamon-screenshot-local`, independentemente do local do clone.
Elas usam as preferências de salvar automaticamente e copiar ao salvar.
O Cinnamon trata ambos os Shifts como o mesmo modificador.

## Instalação para o usuário

```sh
./install-screenshot.py
```

Instala somente este aplicativo, sem compilar ou substituir o desktop:

- Lançador: `~/.local/bin/cinnamon-screenshot-local`.
- Código e recursos: `~/.local/share/cinnamon-screenshot-local`.
- Entrada do menu: **Cannelia Capture**, com ícone e interface em pt_BR.
- Preferências: `~/.config/cinnamon-screenshot-local`.
- Cache compilado: `~/.cache/cinnamon-screenshot-local`.

Na primeira instalação, as preferências deste clone são copiadas. Atualizar
executando o instalador novamente preserva as preferências da instalação.
O instalador configura os três atalhos, verifica conflitos e guarda os
valores anteriores. `--no-shortcuts` instala sem alterá-los. A cópia instalada
funciona mesmo que este clone seja movido ou removido.

Para remover e restaurar os atalhos anteriores (preferências são preservadas):

```sh
/usr/bin/python3 ~/.local/share/cinnamon-screenshot-local/install-screenshot.py --uninstall
```

`--prefix /pasta/temporaria --no-shortcuts` permite validar uma instalação
isolada. Depois de editar o clone, execute o instalador para atualizar a
versão usada no menu e nos atalhos.

## Captura, falhas e concorrência

PNG novo pode ser gravado diretamente pelo compositor no destino. Sem
cópia para a área de transferência, esse fluxo evita decodificar a imagem.
No Cinnamon 6.6, copiar ainda exige carregar o PNG para o GTK; a regravação
do arquivo é eliminada. Outros formatos, arquivos já existentes e o editor
usam salvamento por arquivo temporário no mesmo diretório e troca atômica,
preservando o arquivo anterior se a codificação falhar.

Temporários e nomes de captura são únicos. Um bloqueio por usuário impede
que duas capturas/seletores estejam ativos simultaneamente. O bloqueio é
liberado ao terminar, cancelar ou encerrar o processo; a janela de edição
e uma notificação já exibida não impedem uma captura posterior. Repetições
enquanto a captura está ocupada são recusadas com uma mensagem.

As notificações substituem a anterior, e a ação Abrir pasta sempre se
refere à captura mais recente. Falhas de serviço, pasta indisponível,
salvamento ou cópia são informadas. Uma pasta inválida não é substituída
silenciosamente pela pasta pessoal. Se o arquivo for salvo e a cópia
falhar, a mensagem distingue os dois resultados. Esc no seletor cancela
sem exibir erro; uma captura cancelada com `--file` retorna código 1.

## Medições

```sh
/usr/bin/python3 tools/benchmark-screenshot.py --full-screen --samples 5 \
  --output .local-screenshot/performance.json
```

O benchmark salva em uma pasta temporária e apaga as imagens em seguida.
Sem `--full-screen`, usa apenas um pixel. Na medição local de 28/10/2026,
com Cinnamon 6.6 e imagem de 1920×1080, as medianas de cinco amostras foram:

| Etapa | Mediana |
| --- | --- |
| Capturar, decodificar e regravar PNG | 434 ms |
| PNG direto do compositor | 225 ms |
| Inicializar `--help`, antes | 170 ms |
| Inicializar `--help`, depois | 47 ms |

A redução de 48% refere-se à etapa de captura e salvamento medida, sem
inicialização do Python, temporizador, cópia ou notificações. Os tempos
variam com o conteúdo da tela, tamanho da imagem e máquina.

`--profile` imprime no stderr um registro JSON com o tempo desde a entrada
no lançador até o arquivo salvo. `--no-notification` desativa notificações
para automação. Ambos podem ser usados com `--file`.
