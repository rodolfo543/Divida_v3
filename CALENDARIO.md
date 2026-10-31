# Calendário da dívida

`calendario.html` lê `data/calendar.json`, sem consultar ou modificar os motores financeiros. A navegação comum usa `navigation.css` e a logo transparente `axs-logo-header.png`. A marca antiga `logo.png`, usada pelo assistente, continua preservada.

Para atualizar a agenda a partir dos cálculos já publicados: `python build_calendar.py`. O build normal de `servidor_dashboard.py` também exporta a agenda e espelha os arquivos em `docs/`.

A exportação lê os 17 instrumentos do cadastro de operações ativas. Cada série é lida uma vez; linhas consolidadas não são somadas novamente. Pagamentos e incorporações são distintos, e incorporações não entram no total de caixa. AMEX integra a amortização, com separação no detalhe. Vencimento identifica a última amortização que zera o saldo no fluxo. Valores por instrumento são apresentados em centavos e os totais somam esses centavos. A origem de cada instrumento é registrada com SHA-256.

As datas vêm do cronograma publicado e não são ajustadas por esta camada. Há notas nos detalhes quando uma data está no fim de semana ou quando o instrumento possui pendência documentada. Eventos passados não são classificados como pagos. Eventos posteriores à data-base local são projeções; a agenda não confirma a liquidação de nenhum pagamento.

A primeira abertura seleciona o próximo compromisso disponível. O botão Hoje retorna à data de Brasília. A página permite mudar mês/ano, filtrar empresa e tipo, clicar em dias, navegar com setas do teclado e abrir os detalhes à direita (abaixo no celular). O arquivo `.ics` exporta apenas os eventos do mês e dos filtros selecionados, como eventos de dia inteiro, sem deslocamento por fuso e sem bloquear disponibilidade.

Verificação: `python -m unittest test_calendar.py` e `node test_calendar.js`. No retrato de 30/10/2026, a agenda contém 1.151 eventos (1.100 PMTs, 34 incorporações e 17 vencimentos). Em 16/11/2026 são 6 eventos e R$ 5.888.981,02 em caixa, separados de R$ 10.292.114,32 de incorporação. A AMEX da AXS 02 em 15/10/2026 preserva o total confirmado de R$ 5 milhões.

## Registro da logo

Ferramenta: habilidade imagegen, modo embutido, edição com fundo transparente. Origem: logo AXS ENERGIA enviada pelo usuário. Saída selecionada: `axs-logo-header.png` (alpha real). A apresentação no cabeçalho usa filtro CSS para tornar as letras legíveis no fundo escuro, preservando a distinção do verde.

Prompt final utilizado:

> Extract the exact flat AXS ENERGIA logo from this image. This is a precise corporate logo cutout, not a redesign. Remove the white background COMPLETELY to genuine transparent alpha. Keep all original black strokes and lettering BLACK; keep the green mark exactly green. Maintain the exact typography and symbol, including AXS and ENERGIA beneath. Clean sharp smooth edges, flat solid opaque fills. Absolutely no texture, no speckles, no distress, no extra pixels outside the logo shapes, no shadow, no border, no mockup. The outside of the logo and all holes inside letters must be 100% transparent. Only the original logo shapes should have any opacity. Use a tightly framed horizontal transparent PNG.
