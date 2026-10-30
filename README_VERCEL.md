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

As referências externas servem exclusivamente à validação: `validate_pu_reference.py` recebe a planilha PUdia e registra tanto a igualdade em centavos quanto em oito casas. São verificações distintas. AXS 05 e AXS 11 têm pendências documentais/externas; não ajustar taxas ou índices para forçar igualdade. Na AXS 04, manter o cronograma documental: a memória examinada difere em 0,0001 ponto percentual nas amortizações de setembro e outubro de 2025.

Verificação local: `python -m unittest test_debt_corrections test_daily_pu test_paxs12` e `node test_daily_pu.js`.
