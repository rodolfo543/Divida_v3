# Conciliação Vórtx

Página separada em `vortx.html`. Não modifica resultados, premissas ou funcionalidades dos motores financeiros.

- `vortx_catalog.json`: vínculo explícito de 17 instrumentos ativos do modelo aos IDs públicos Vórtx; pendências e notas de auditoria.
- `build_vortx_comparison.py`: lê os JSONs financeiros já publicados, gera retratos compactos em `data/vortx` e espelha em `docs/data/vortx`. Integrado ao build normal. Para renovar só esta camada: `python build_vortx_comparison.py`. Para renovar apenas o espelho do cálculo local preservando a referência coletada: `python build_vortx_comparison.py --offline`.
- `api/vortx.js`: consulta GET dos três endpoints públicos (histórico, prévia e ficha), sem chave, com IDs permitidos, timeout, cache de 5 minutos e fallback para o último retrato. Não é um proxy aberto. Não grava os valores oficiais no cálculo local.
- `vortx-core.js`: comparação decimal com inteiros escalados a 10⁸; igualdade em centavos compara cada fonte arredondada. Nunca converter números ausentes em zero. Gráficos usam ponto flutuante apenas para coordenadas visuais.

O PU vazio é harmonizado como **PU cheio menos pagamento por título** nesta comparação, pois alguns motores usam o nome “PU vazio” para o nominal. O campo original fica preservado no retrato em `empty_model`. Amortização ordinária usa `ordinaryCashflowAmount`, sem somar novamente a AMEX já incluída em `amortization`. Eventos das séries locais estimadas da AXS 05 ficam ausentes em vez de repetir os valores do próximo vencimento transportados pelo `raw` da interpolação.

Histórico e prévia são separados. Nenhuma projeção local posterior à data-base entra nos indicadores históricos. A prévia é limitada às datas retornadas pela Vórtx, com projeções locais até 180 dias da geração. Quantidades são do modelo, não posição em custódia. Impactos de instrumentos com pendência ou série estimada ficam fora dos totais por padrão; o usuário pode incluí-los explicitamente.

Retrato inicial em 30/10/2026: 17 instrumentos com par; 1 coincide nas 8 casas, 14 coincidem em centavos (incluindo o exato), 3 divergem em centavos. AXS 05 (duas séries) e AXS 11 continuam com as pendências documentadas, sem ajuste forçado ao dado oficial.

Verificação: `python -m unittest test_vortx_comparison.py` e `node test_vortx_comparison.js`; regressões financeiras existentes continuam aplicáveis. A origem de cada retrato é rastreável pelo SHA-256 do JSON financeiro usado. Os JSONs Vórtx são referências isoladas, jamais entradas dos motores.
