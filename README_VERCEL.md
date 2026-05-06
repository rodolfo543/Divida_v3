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
