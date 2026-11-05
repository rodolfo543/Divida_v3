# Registro da publicação

As mudanças abaixo foram aprovadas para publicação. O estado anterior está no commit Git 14d57d7; o texto a seguir registra a etapa de prévia e suas referências locais.

# Revisão de textos — prévia local do dash_v2

Criada em 04/11/2026. Esta prévia usa cópias das páginas e scripts do dash_v2 e lê as bases existentes em dash_v2/data. Os arquivos do site e da publicação não foram alterados.

Os arquivos originais alterados estão na pasta `original/`. Para desfazer a revisão, copie-os para a raiz desta prévia. Para incorporar as mudanças ao site depois da revisão, aplique-as aos arquivos-fonte correspondentes do dash_v2.

## index.html

- **Antes:** <p class="eyebrow">Controle executivo</p>
  **Depois:** (removido)
- **Antes:** <h1>Controle de d&iacute;vida - AXS Energia</h1>
  **Depois:** <h1>Carteira de dívida</h1>
- **Antes:** Dashboard visual para acompanhar cada emissão, consolidar a carteira e navegar pelos cálculos dos scripts Python com muito mais contexto financeiro.
  **Depois:** Saldos, pagamentos e condições das operações.
- **Antes:** Preparando o dashboard.
  **Depois:** Carregando informações.
- **Antes:** Escolha a análise
  **Depois:** Selecione uma operação
- **Antes:** <p class="section-note">Use a visão geral para consolidado e cada aba individual para aprofundar a dívida.</p>
  **Depois:** (removido)
- **Antes:** PMT por evento
  **Depois:** Pagamentos por data
- **Antes:** <p class="section-note">Leitura do comportamento dos pagamentos no tempo.</p>
  **Depois:** (removido)
- **Antes:** <p class="section-note">Saldo atual corrigido pela data corrente da carteira.</p>
  **Depois:** (removido)
- **Antes:** Juros x amortização
  **Depois:** Juros e amortização
- **Antes:** <p class="section-note">Comparação direta entre as duas pernas do fluxo.</p>
  **Depois:** (removido)
- **Antes:** Radar da carteira inteira, mesmo quando uma dívida específica estiver selecionada.
  **Depois:** Todas as operações da carteira, independentemente da seleção.
- **Antes:** <p class="section-kicker">Radar</p>
  **Depois:** <p class="section-kicker">Carteira</p>
- **Antes:** Carteira em destaque
  **Depois:** Saldos e próximos pagamentos
- **Antes:** <p class="section-note">Cards com saldos e próximos PMTs para leitura rápida.</p>
  **Depois:** (removido)
- **Antes:** <p class="section-note">Linha do tempo operacional da seleção atual.</p>
  **Depois:** (removido)

## dashboard.js

- **Antes:** Saldo na data corrente da seleção.
  **Depois:** Saldo da operação selecionada.
- **Antes:** Principal capturado na linha mais recente aplicavel.
  **Depois:** Principal na linha mais recente aplicável.
- **Antes:** Prazo medio ponderado pelos PMTs futuros.
  **Depois:** Prazo médio ponderado pelos PMTs futuros.
- **Antes:** Prazo medio ponderado pelas amortizacoes futuras.
  **Depois:** Prazo médio ponderado pelas amortizações futuras.
- **Antes:** Arredondado para leitura rapida.
  **Depois:** Arredondado para duas casas decimais. (2 ocorrências)

## vortx.html

- **Antes:** <p class="section-kicker">Controle e transparência</p><h1>Do cálculo à conferência.</h1><p>Compare a carteira com a Vórtx, encontre a origem de cada diferença e acompanhe seu impacto financeiro.</p>
  **Depois:** <h1>Conciliação Vórtx</h1><p>Compare os cálculos da AXS com os valores publicados pela Vórtx.</p>
- **Antes:** <p class="section-kicker">Visão executiva</p><h2>A carteira, lado a lado</h2>
  **Depois:** <h2>Comparação por instrumento</h2>
- **Antes:** Investigação por instrumento
  **Depois:** Instrumento

## calendario.html

- **Antes:** <p class="section-kicker">Agenda financeira</p>
  **Depois:** (removido)
- **Antes:** PMTs, recomposições, vencimentos e incorporações. Selecione um dia para abrir o detalhe.
  **Depois:** Pagamentos, recomposições, vencimentos e incorporações. Selecione um dia para ver os detalhes.


## Cartão das operações — 04/11/2026

- Antes: todos os campos da aba Informações apareciam de uma vez; agora, os principais aparecem primeiro e os demais ficam em “Mais informações”, sem remoção de campos. As abas PU e Fontes continuam disponíveis.
- Antes: valores textuais em campos relacionados a juros, amortização ou saldo podiam ser tratados como dinheiro e aparecer como “-”. Agora são exibidos como texto; valores numéricos continuam formatados. Na AXS 03, pagamento de juros e amortização passam a mostrar “Mensal”, conforme a base existente. Na visão geral, o nome da emissão com maior saldo também deixa de ser ocultado.
- Antes: dados ausentes apareciam como “-”; nos campos das abas Informações e PU, agora aparecem como “Não informado”. Garantias da AXS 03 continua sem valor na base e não foi presumida.
- O cartão deixa de se esticar para acompanhar a altura da coluna ao lado. O estilo da seção recolhível foi adicionado em dashboard.css.
- Arquivos anteriores à revisão guardados em original/dashboard.js e original/dashboard.css. Os dados e cálculos originais não foram alterados.
- O script revisar.cjs registra apenas a primeira revisão de textos; executá-lo novamente substitui as alterações posteriores no dashboard.js e no registro. Preserve os arquivos atuais antes de usá-lo.

## Resumo da carteira e agenda — 04/11/2026

- O bloco de comparação, antes visível em todas as seleções, agora aparece apenas na visão geral e recebeu o título “Resumo por operação”. Mantém os mesmos valores e limite anterior de dez operações, com rótulos e valores organizados.
- “Próximos eventos” identifica a seleção e inclui um link para o calendário completo. O link abre o calendário geral, sem aplicar automaticamente filtro por operação.
- Alterados index.html, dashboard.js e dashboard.css apenas na prévia. Versões anteriores à revisão inicial estão em original/. Não execute revisar.cjs sem preservar os arquivos atuais, pois ele recria a revisão inicial.

## Gráficos e abas da conciliação Vórtx — 04/11/2026

- “Histórico publicado” passou a “Histórico de PUs”; “Prévia Vórtx” passou a “Previsão de pagamentos”. A origem e a natureza de prévia dos dados permanecem indicadas na página.
- Os gráficos ganharam explicações e um título próprio para a diferença por título. A sobreposição das duas linhas no primeiro gráfico representa valores próximos; o segundo mostra a diferença entre as fontes.
- Corrigida a altura dos contêineres, que herdavam uma altura fixa do dashboard e deixavam espaços excessivos. Dados e cálculos dos gráficos não foram alterados.
- Original de vortx.css preservado em original/; original de vortx.html já estava guardado. Alterações apenas na prévia.
