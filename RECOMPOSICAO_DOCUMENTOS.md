# Recomposição e documentação

## Escopo do Financeiro

Recomposição de caixa planejada a partir de 1/6 das PMTs semestrais; sem acesso a contas, sem abater saldos, sem confirmar transferências e sem módulo de obrigações. A AXS 10 foi expressamente separada pelo usuário por possuir fundo estático no contrato refinanciado. A biblioteca usa apenas documentos públicos da Vórtx, sem publicar os PDFs ou outros arquivos locais da empresa.

## Recomposição

`recomposition_rules.json` registra aplicabilidade, natureza, início e encerramento por instrumento e as cláusulas de referência. O contrato refinanciado de março/2026 da AXS 06 abrange as duas emissões. A retenção de 1/6 começa no sexto mês anterior à primeira amortização programada; juros pagos durante a carência não antecipam esse início. Para Goiás, isso significa dezembro/2026, pois a primeira amortização é junho/2027; a PMT de juros de dezembro/2026 não é o marco inicial. As referências subordinadas de AXS 01/05 são sujeitas à cascata e não se confundem com exigência incondicional.

`build_recomposition.py` lê `data/calendar.json`, já exportado pelos cálculos independentes, e gera `data/recomposition.json` mais o espelho em `docs`. Nenhum motor ou PU oficial é alterado. Dez instrumentos participam; sete ficam fora do rateio (mensais, bullet e AXS 10). O encerramento após a penúltima PMT é respeitado quando previsto; AXS 08 e as séries subordinadas mantêm a composição até a última PMT conforme a regra cadastrada.

Convenção mensal de planejamento: as seis competências anteriores ao mês da PMT financiam essa PMT; no mês de seu pagamento inicia o ciclo da próxima. Não se infere data de transferência. O dia 12 é mostrado apenas como referência de verificação contratual, quando previsto. O rateio arredonda acumulados proporcionais em centavos: a diferença entre parcelas é de no máximo um centavo, e a soma das seis parcelas fecha a PMT projetada. O acumulado mostrado é programado, não saldo real ou confirmação de aportes passados.

Na base de 30/10/2026, outubro tem AXS 08 R$ 1.273.332,94 e AXS 09 R$ 1.472.630,66, total R$ 2.745.963,60. As demais séries aplicáveis estão em carência nessa competência. O usuário escolhe mês/empresa/situação, consulta o ciclo de seis aportes, projeta 12 competências e exporta os filtros para CSV. Pendências dos PUs de AXS 05 e AXS 11 permanecem identificadas.

Fontes examinadas, preservadas no arquivo local de auditoria em `../auditoria/2026-10-30/recomposicao`: cessões fiduciárias refinanciadas AXS 01 e 05 (57174703.1 e 57174695.1), CF AXS 06 refinanciada (57300530v1), contrato CF AXS 08, CF AXS 09 e primeiro aditivo, CF AXS 10 refinanciada de 20/05/2026, primeiro aditivo CF sênior Goiás (12484652v1), primeiro aditivo CF AXS 11. O cadastro público contém somente nomes e referências das cláusulas, sem caminhos privados ou dados bancários.

## Documentação

`build_documents.py` coleta as rotas públicas `/{id}/documentos-por-tipo/0` e `/1`, reúne os grupos pelo tipo efetivamente retornado, exige `public=true`, valida o domínio HTTPS Vórtx e deduplica pelos IDs. Esses números de rota não são tratados como tipos documentais. O catálogo inicial tem 386 documentos únicos e 17 instrumentos de 13 empresas. Os arquivos compartilhados são contados uma vez no escopo da empresa. Pastas vazias não são apresentadas como prova de inexistência de documentos.

`data/documents.json` guarda apenas metadados públicos; não contém assinaturas temporárias de URLs, IDs de usuário ou PDFs. A interface `documentos.html` organiza empresa → operação/instrumento → tipo, com busca em subpastas, filtros por tipo/ano, detalhes e CSV. Títulos amigáveis de categorias não alteram o tipo original, preservado nos detalhes. Publicação é a data do catálogo, não atestado de vigência contratual.

`api/documentos.js` aceita somente códigos do catálogo e IDs numéricos. Na abertura, renova a lista e redireciona somente para um arquivo público devolvido pela Vórtx em domínio permitido; não aceita uma URL arbitrária. Cache de cinco minutos, com renovação se o link estiver perto de vencer. Em falha de coleta, os metadados anteriores mantêm a data original. Um link indisponível por falha da fonte pode levar à pasta pública da operação para consulta. A atualização na página atualiza sua sessão; o build persiste o próximo retrato.

## Publicação e validação

`navigation.py` centraliza as cinco abas em HTML estático, mantendo a logo e a identificação da aba ativa. `servidor_dashboard.py` exporta calendário → recomposição → conciliação Vórtx → documentos; também espelha os novos assets em `docs/`. Para atualizar apenas as novas camadas a partir dos cálculos publicados: `python build_recomposition.py` e `python build_documents.py`.

Testes: `python -m unittest test_recomposition_documents.py`, `node test_documents.js`, regressões `node test_daily_pu.js` e `node test_vortx_comparison.js`. Cobrem carências, Goiás, duas emissões AXS 06, AXS 10 fora do total, fim na penúltima PMT, seis aportes fechando a PMT, integridade da origem, documentos públicos, domínios, deduplicação, falhas e validação dos endpoints. Os motores e os JSONs financeiros originais permanecem preservados.
