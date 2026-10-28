# Histórico de versões

## Não lançado

- Código concentrado em `src/cannelia_capture/`, sem a hierarquia do desktop Cinnamon.
- Removidos licença duplicada, guia redundante, ícone sem uso e utilitário de
  criação inicial do repositório; mantidos licença integral e avisos de origem.
- Instruções de desenvolvimento e empacotamento consolidadas em CONTRIBUTING.md.

## 1.0.0 — 2026-10-28

- Primeira release pública com pacote Debian independente (`Architecture: all`).
- Comando `cannelia-capture`, entrada no menu e ícone próprio do pacote.
- Tradução pt-BR e schema compilados durante o empacotamento.
- Preferências compartilhadas com a instalação por usuário existente.
- `--version`, instruções de instalação/remoção e build reproduzível do `.deb`.
- Dependências declaradas para instalação pelo APT; licença e créditos incluídos.

## 0.1.0 — 2026-10-28

Primeira versão independente do **Cannelia Capture**, derivada do
`cinnamon-screenshot` do Linux Mint.

- GUI compacta, botões de modo destacados, ação principal em largura total
  e cantos inferiores arredondados pelo tema.
- Temporizador, ponteiro e sombra nas Preferências; remoção de Opções,
  Fechar, texto introdutório e espaços vazios desnecessários.
- Tradução pt-BR, identidade Cannelia Capture e diálogo Sobre com licença.
- Pasta Imagens e salvamento/cópia automáticos ativos por padrão.
- Atalhos Super + Shift + A/S/D para tela, região e janela.
- Compatibilidade com a interface de captura do Cinnamon 6.6.
- Correção de recortes fora da imagem, oito alças, movimentação, dimensões,
  zoom até 400%, rolagem e desfazer sem cópias desnecessárias dos pixels.
- Compilação de configurações sob demanda, PNG direto, gravação atômica,
  nomes únicos, bloqueio de concorrência e notificações substituíveis.
- Mensagens de falha, cancelamento sem erro e diagnóstico `--check`.
- Instalador por usuário, entrada no menu, backup/restauração de atalhos,
  atualização e remoção preservando preferências.
- Testes de regressão, benchmark reproduzível e documentação de proveniência.

Os detalhes, limites e evidências estão em [docs/CHANGES.md](docs/CHANGES.md).
