# Dashboard de Divida - AXS Energia

Pacote pronto para publicar na Vercel.

## Arquivos principais

- `index.html`, `dashboard.css`, `dashboard.js`: dashboard estatico.
- `data/`: bases JSON ja calculadas que alimentam o dashboard e a IA.
- `api/chat.js`: micro-backend da IA usando NVIDIA.
- `api/chunks.json`: base textual dos documentos para o Assistente AXS.
- `logo.png`: logo exibida no chat.
- `vercel.json`: configuracao da funcao serverless.

## Configuracao na Vercel

1. Suba esta pasta para o repositorio do GitHub.
2. Na Vercel, importe o repositorio.
3. Em `Environment Variables`, crie a variavel `NVIDIA_API_KEY` com a chave da NVIDIA.
4. Opcionalmente, crie `NVIDIA_MODEL` se quiser trocar o modelo. Se nao criar, sera usado `google/gemma-4-31b-it`.
5. Em `Build Command`, deixe em branco.
6. Em `Output Directory`, deixe em branco.
7. Clique em `Deploy`.

## Atualizacao dos dados

Quando os scripts Python forem atualizados, rode localmente:

```powershell
cd "C:\Users\rodolfo.crotti\OneDrive - AXS ENERGIA S A\Documents\Desenvolvimento\Cálculo da dívida\dash_v2"
python .\servidor_dashboard.py build
```

Depois suba novamente os arquivos alterados para o GitHub. A Vercel faz o redeploy automaticamente.

## Observacao sobre tempo da IA

Algumas perguntas podem demorar mais porque a funcao consulta a API da NVIDIA com trechos dos documentos e dados calculados. Se a NVIDIA passar do limite seguro, o chat devolve uma resposta parcial usando diretamente os calculos do dashboard em vez de quebrar com erro 500.

## Cálculos e conciliação de PU

Os motores usam índices e regras contratuais. O histórico Vórtx não substitui os resultados calculados. A publicação da projeção corrente da ANBIMA fica identificada em `data/market/anbima_ipca.json`; as projeções posteriores continuam usando Focus. Eventos financeiros confirmados são insumos separados, como a amortização de R$ 5 milhões da AXS 02 em `data/events/axs02.json`.

`daily_contracts.py` calcula cada dia por correção monetária e juros, sem interpolar o PU de um pagamento futuro. As séries nativas da AXS 01/02 e os cálculos da AXS 10, Goiás e PAXS12 continuam nos respectivos motores. A AXS 05 conserva sua aproximação diária identificada na tela e tem a taxa AXSC12 corrigida para 9,3515% a.a.

As referências externas de PU servem à validação: `validate_pu_reference.py` recebe a planilha PUdia e registra tanto a igualdade em centavos quanto em oito casas. São verificações distintas. AXS 05 e AXS 11 têm pendências documentais/externas; não ajustar taxas ou índices para forçar igualdade. Na AXS 04, o cronograma documental permanece registrado, e os percentuais dos dois eventos já liquidados em 2025 seguem a informação operacional da Opea em `data/events/axs04.json`. Na AXS 02, o valor do CRI é baseado na amortização extraordinária divulgada pela Opea; a debênture recebe o restante dos R$ 5 milhões confirmados.

Verificação local: `python -m unittest test_debt_corrections test_daily_pu test_paxs12` e `node test_daily_pu.js`.

## AXS 02: amortizações mensais de 2026 e 2027

As atas de novembro/2026 preveem R$ 211.764,80 por mês para o CRI e R$ 188.235,20 para a debênture, de novembro/2026 a outubro/2027. A Vórtx registra a primeira amortização em 16/11/2026. As minutas consolidadas anexas às atas indicam início em dezembro, mas a ordem do dia e o evento efetivamente registrado pela Vórtx indicam novembro. Cash sweep é adicional e depende de apuração; não foi presumido no fluxo.

Em 24/11/2026, os PUs cheios calculados foram 1016,38628456 (CRI) e 1013,46443194 (debênture), ante 1016,38626617 e 1013,46426612 na Vórtx, respectivamente: coincidem em centavos, com diferenças nas casas posteriores. Valores externos são usados apenas para conferência.

## Goiás: AGD de 10/11/2026 e segundo aditamento

O motor `Code final prontos/axs_goias_v1.py` incorpora os juros de 15/12/2026, 15/06/2027 e 15/12/2027, sem pagamento de juros ou amortização nessas datas. O novo Anexo VI prevê 28 pagamentos semestrais de 15/06/2028 a 15/12/2041; os percentuais incidem sobre o saldo remanescente.

O prêmio de 1% incide sobre o saldo devedor com juros corridos em 10/11/2026 e integra o VNA sem desembolso. A correção monetária e os juros sobre esse acréscimo começam nessa data; os juros anteriores continuam no período original até sua incorporação. O calendário identifica o prêmio separadamente dos juros incorporados, e a variação mensal o separa da atualização pelo IPCA. A recomposição de 1/6 começa em dezembro/2027, seis meses antes da primeira amortização.

Os documentos de suporte estão no acervo de Goiás em `documents-supplemental.json`. Verificação: `python -m unittest test_goias_aditamento test_goias_precision test_calendar test_recomposition_documents test_vortx_comparison` e `node test_calendar.js`.
