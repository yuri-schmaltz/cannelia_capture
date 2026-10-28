# O que foi feito

Esta distribuição parte do aplicativo Python `cinnamon-screenshot` existente
na revisão `d67b361f90bccc3346fe342b2a571b68ec1eb671` do Cinnamon e inclui
somente os arquivos necessários ao aplicativo, seus testes e sua documentação.
O desktop Cinnamon completo não é compilado nem redistribuído aqui.

## Identidade e interface

O produto foi renomeado para **Cannelia Capture** na janela, nas Preferências,
no menu da distribuição, nas notificações e na ajuda. A seção Sobre apresenta
versão, mantenedor, créditos, repositório e GPL v2 ou posterior. Os nomes
internos anteriores foram preservados para manter instalações e configurações.

A tela inicial foi reduzida aos quatro modos e ao botão principal, agora
em largura total. Foram removidos o texto introdutório, a área vazia de
prévia, o botão Fechar e o espaço excedente abaixo da ação principal.
Os cantos inferiores seguem o arredondamento do tema Mint-Y por meio da
classe GTK `unified`, preservando a união visual com a barra de título.

O temporizador, o cursor e a sombra foram movidos do popover Opções para
**Preferências → Captura**. A prévia, Recortar, Desfazer, Copiar e Salvar
aparecem depois de existir uma imagem. Salvar mantém a prévia disponível
e mostra o resultado, com a ação Abrir pasta.

## Padrões e integração

A pasta padrão passou a ser a pasta Imagens resolvida pelo XDG do usuário.
O lançador isolava `XDG_CONFIG_HOME` e perdia `user-dirs.dirs`; ele agora
preserva essa definição na configuração isolada. Salvamento automático e
cópia ao salvar passaram a estar ativos por padrão.

Os atalhos definidos são Super + Shift + A (tela), S (região) e D (janela).
O instalador verifica conflitos, cria ou atualiza suas entradas e guarda os
valores anteriores para a remoção. Outros atalhos são preservados.

O adaptador `LegacyBackend` usa o serviço já disponível no Cinnamon 6.6.
O flash, inicialmente fixado como desativado nesse adaptador, foi corrigido
para ler a preferência. A cópia é feita pelo GTK quando o compositor antigo
não a implementa. Os limites de seleção de janela, cursor e sombra estão
explicados no README.

## Recorte e memória

O recorte original podia produzir uma coordenada igual à largura/altura da
imagem e chamar `.copy()` sobre um subpixbuf inexistente. A correção inicial
limitou a interseção à imagem. A implementação final mantém a seleção em
coordenadas de pixels, separada da escala da prévia.

Foram adicionadas oito alças, movimentação da seleção, dimensões, zoom até
400% e barras de rolagem. Arrastar para fora limita a seleção às bordas;
clicar inteiramente na margem não cria um recorte inválido. Desfazer restaura
a imagem anterior. Recortes compartilham os pixels do pai, sem uma cópia
integral desnecessária; o histórico mantém as referências necessárias.

## Desempenho e segurança do salvamento

O lançador deixou de recompilar schemas a cada execução e passou a comparar
a assinatura da fonte. Os catálogos são compilados somente quando mudam.
A compilação concorrente é protegida por bloqueio. `--help` usa o parser
sem importar GTK ou inicializar serviços.

Um novo PNG pode ser solicitado diretamente no destino ao compositor. O
arquivo é reservado com criação exclusiva; erro remove essa reserva. No
backend antigo, o PNG só é decodificado para a área de transferência quando
necessário. Os outros fluxos usam arquivo temporário no mesmo diretório e
`os.replace`, preservando arquivos existentes caso a codificação falhe.

Nomes de capturas incluem horário com microssegundos e um identificador
aleatório. Temporários são criados com `mkstemp`, em um diretório por usuário.
Um bloqueio `flock` impede seletores/capturas concorrentes, inclusive entre
processos. Popups sucessivos substituem a notificação anterior; uma ação
de notificação ultrapassada não abre o arquivo errado.

## Falhas e diagnósticos

Pastas inválidas não são substituídas silenciosamente. Há mensagens para
falhas de serviço, gravação e cópia. Uma cópia malsucedida não transforma
um salvamento válido em uma falsa falha de gravação. Cancelar o seletor
não mostra um erro; com destino explícito, retorna código de saída 1.

`--check` verifica a carga da interface e o backend sem capturar. `--profile`
mede até o arquivo salvo e `--no-notification` atende automações. A combinação
`--clipboard --file` salva e copia, e `--delay` é validado entre 0 e 3.600.

## Instalação e publicação

O instalador copia apenas o app para o perfil do usuário, registra o menu,
migra as preferências iniciais e configura os atalhos. Atualizar preserva
as configurações. Remover restaura os atalhos anteriores ainda gerenciados
e preserva as preferências. Há validação de prefixos com espaços e de uma
instalação independente do clone.

A distribuição independente traz README próprio, GPL integral, autoria,
proveniência do upstream, contrato D-Bus extraído para testes, catálogo pt-BR,
capturas de demonstração e fluxo de CI dedicado ao aplicativo.

## Evidências e limites

Foram verificados: captura PNG real, cópia real à área de transferência,
falha real de destino, instalação no menu, atalhos, GUI, preferências,
recorte e zoom. Os testes automatizados usam imagens sintéticas e cobrem
geometria, estados da GUI, salvamento, concorrência, notificações,
compatibilidade D-Bus e instalação/remoção.

Na medição local de cinco amostras, em 1920×1080 e Cinnamon 6.6, o caminho
com decodificação/regravação teve mediana de 434 ms; o caminho direto, 225 ms.
São medições de uma etapa específica, não uma garantia de latência universal.
O teste de contrato do serviço moderno não substitui um teste funcional em
um Cinnamon novo ou em Wayland. Este repositório não modifica o compositor.
