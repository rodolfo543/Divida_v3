const fs = require("fs");
const path = require("path");

let chunksCache = null;
let manifestCache = null;
const payloadCache = new Map();

const OPERATIONS = {
  geral: ["visao geral", "carteira", "consolidado", "geral"],
  axs01: ["axs 01", "axs01", "refi 01", "axsa11", "axsa21", "unidade 01"],
  axs02: ["axs 02", "axs02", "axsd11", "cri axs 02", "deb axs 02", "unidade 02"],
  axs03: ["axs 03", "axs03", "axs iii", "22k1397969", "emissao 78"],
  axs04: ["axs 04", "axs04", "axs 4", "23f0046476", "emissao 139"],
  axs05: ["axs 05", "axs05", "axsc12", "axsc22", "unidade 05"],
  axs06: ["axs 06", "axs06", "axse12", "unidade 06"],
  axs07: ["axs 07", "axs07", "axsu11", "unidade 07"],
  axs08: ["axs 08", "axs08", "axs811", "unidade 08"],
  axs09: ["axs 09", "axs09", "axs911", "unidade 09"],
  axs10: ["axs 10", "axs10", "axs411", "unidade 10"],
  axs11: ["axs 11", "axs11", "axsi11", "unidade 11"],
  axsgoias: ["axs goias", "axs goiás", "goias", "goiás", "axs311", "ufv goias"],
};

function repoRoot() {
  return path.join(__dirname, "..");
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function loadChunks() {
  if (!chunksCache) {
    chunksCache = require("./chunks.json");
  }
  return chunksCache;
}

function loadManifest() {
  if (!manifestCache) {
    manifestCache = readJson(path.join(repoRoot(), "data", "operations.json"));
  }
  return manifestCache;
}

function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\w\s/.-]/g, " ");
}

function detectOperation(question) {
  const q = normalize(question);
  const matches = [];
  for (const [id, aliases] of Object.entries(OPERATIONS)) {
    for (const alias of aliases) {
      const a = normalize(alias).trim();
      if (a && q.includes(a)) matches.push({ id, score: a.length });
    }
  }
  matches.sort((a, b) => b.score - a.score);
  return matches[0]?.id || "geral";
}

function detectVariant(operationId, question) {
  const q = ` ${normalize(question)} `;
  if (operationId === "axs02") {
    if (q.includes(" deb ") || q.includes("debenture")) return "deb";
    if (q.includes(" cri ")) return "cri";
    return "total";
  }
  if (operationId === "axs01" || operationId === "axs05") {
    if (q.includes("primeira serie") || q.includes("1a serie") || q.includes("serie 1") || q.includes("axsa11") || q.includes("axsc12")) return "primeira";
    if (q.includes("segunda serie") || q.includes("2a serie") || q.includes("serie 2") || q.includes("axsa21") || q.includes("axsc22")) return "segunda";
    return "total";
  }
  return "";
}

function payloadFilename(operationId, variantId) {
  if (variantId && variantId !== "total") return `${operationId}--${variantId}.json`;
  return `${operationId}.json`;
}

function loadPayload(operationId, variantId) {
  const fileName = payloadFilename(operationId, variantId);
  if (payloadCache.has(fileName)) return payloadCache.get(fileName);
  const filePath = path.join(repoRoot(), "data", "operations", fileName);
  const payload = readJson(filePath);
  payloadCache.set(fileName, payload);
  return payload;
}

function extractDate(question) {
  const match = String(question || "").match(/\b(\d{2}\/\d{2}\/\d{4})\b/);
  return match ? match[1] : null;
}

function parseBrDate(value) {
  const match = String(value || "").match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (!match) return null;
  return new Date(Number(match[3]), Number(match[2]) - 1, Number(match[1]));
}

function fieldLookup(payload, label) {
  const target = normalize(label).trim();
  const op = payload.operation || {};
  const fields = [
    ...(op.identity_fields || []),
    ...(op.overview_fields || []),
    ...(op.pu_fields || []),
  ];
  const field = fields.find((item) => normalize(item.label).trim() === target);
  return field ? String(field.value ?? "-") : "-";
}

function rowsOnDate(payload, dateText) {
  const rows = payload.table_series || payload.series || [];
  return rows.filter((row) => row.date === dateText);
}

function rowAtOrBefore(payload, dateText) {
  const target = parseBrDate(dateText);
  if (!target) return null;
  const rows = payload.series || [];
  return rows
    .map((row) => ({ row, parsed: parseBrDate(row.date) }))
    .filter((item) => item.parsed && item.parsed <= target)
    .sort((a, b) => a.parsed - b.parsed)
    .at(-1)?.row || null;
}

function paymentRows(payload) {
  return (payload.series || []).filter((row) => Number(row.payment || 0) > 0);
}

function money(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toFixed(2) : String(value ?? "-");
}

function buildPortfolioContext(payload) {
  const comparison = payload.comparison || [];
  return comparison.slice(0, 14).map((item) => (
    `${item.label}: saldo atual ${money(item.current_balance)}, proximo PMT ${money(item.next_payment_amount)}, indexador ${item.indexer}`
  )).join("\n");
}

function buildCalculationContext(question, payload) {
  const summary = payload.summary || {};
  const operation = payload.operation || {};
  const dateText = extractDate(question);
  const q = normalize(question);
  const lines = [
    `Operacao: ${operation.full_name || operation.label || "-"}`,
    `Identificador: ${operation.id || "-"}`,
    `Tipo: ${operation.badge || "-"} / ${operation.category || "-"}`,
    `Indexador: ${operation.indexer || "-"}`,
    `Remuneracao: ${fieldLookup(payload, "Remuneracao")}`,
    `Data de emissao: ${fieldLookup(payload, "Data de emissao")}`,
    `Data de vencimento: ${fieldLookup(payload, "Data de vencimento")}`,
    `Volume emitido: ${fieldLookup(payload, "Volume emitido")}`,
    `Quantidade emitida: ${fieldLookup(payload, "Quantidade emitida")}`,
    `Garantias: ${fieldLookup(payload, "Garantias")}`,
    `Saldo atual: ${money(summary.current_balance)}`,
    `Principal atualizado: ${money(summary.current_principal)}`,
    `PU cheio atual: ${summary.current_pu_cheio ?? "-"}`,
    `PU vazio atual: ${summary.current_pu_vazio ?? "-"}`,
    `Juros acumulados: ${money(summary.total_interest)}`,
    `Amortizacao acumulada: ${money(summary.total_amortization)}`,
    `Duration em anos: ${summary.duration_years ?? "-"}`,
    `Vida media em anos: ${summary.wal_years ?? "-"}`,
    `Proximo PMT data: ${summary.next_payment_date || "-"}`,
    `Proximo PMT valor: ${money(summary.next_payment_amount)}`,
    `Proximo PMT juros: ${money(summary.next_interest_amount)}`,
    `Proximo PMT amortizacao: ${money(summary.next_amortization_amount)}`,
  ];

  if (operation.id === "geral") {
    lines.push("Resumo da carteira:");
    lines.push(buildPortfolioContext(payload));
  }

  const payments = paymentRows(payload);
  const firstPayment = payments[0];
  const lastPayment = payments.at(-1);
  if (firstPayment) lines.push(`Primeira PMT positiva: ${firstPayment.date} | PMT ${money(firstPayment.payment)} | Juros ${money(firstPayment.interest)} | Amortizacao ${money(firstPayment.amortization)} | Saldo ${money(firstPayment.balance)}`);
  if (lastPayment) lines.push(`Ultima PMT positiva: ${lastPayment.date} | PMT ${money(lastPayment.payment)} | Juros ${money(lastPayment.interest)} | Amortizacao ${money(lastPayment.amortization)} | Saldo ${money(lastPayment.balance)}`);

  if (dateText) {
    const exactRows = rowsOnDate(payload, dateText);
    if (exactRows.length) {
      for (const row of exactRows.slice(0, 10)) {
        lines.push(`Linha exata ${dateText}: tipo ${row.component_label || "-"} | evento ${row.label || "-"} | PMT ${money(row.payment)} | juros ${money(row.interest)} | amortizacao ${money(row.amortization)} | PU cheio ${row.pu_cheio ?? "-"} | PU vazio ${row.pu_vazio ?? "-"} | saldo ${money(row.balance)}`);
      }
    } else {
      lines.push(`Nao ha linha exata para ${dateText}. Se a pergunta for PMT nessa data, responder que nao ha pagamento programado nessa data e que o PMT e zero, salvo se o documento disser algo diferente.`);
    }
    const previous = rowAtOrBefore(payload, dateText);
    if (previous) {
      lines.push(`Linha de referencia ate ${dateText}: data ${previous.date} | evento ${previous.label} | saldo ${money(previous.balance)} | principal ${money(previous.principal)} | PU cheio ${previous.pu_cheio ?? "-"} | PU vazio ${previous.pu_vazio ?? "-"}`);
    }
  }

  if (q.includes("ultima") && lastPayment) {
    lines.push("A pergunta menciona ultima PMT; use a linha 'Ultima PMT positiva' como referencia principal.");
  }

  return lines.filter(Boolean).join("\n");
}

function expandQuestion(question) {
  const q = normalize(question);
  const expansions = [];
  if (q.includes("pmt") || q.includes("pagamento") || q.includes("pagar")) expansions.push("pagamento amortizacao juros fluxo cronograma parcela");
  if (q.includes("saldo")) expansions.push("saldo devedor valor nominal atualizado principal");
  if (q.includes("garantia")) expansions.push("garantias fianca alienacao fiduciaria cessao fiduciaria");
  if (q.includes("vencimento") || q.includes("vence")) expansions.push("vencimento prazo final");
  if (q.includes("taxa") || q.includes("remuneracao") || q.includes("juros")) expansions.push("juros remuneratorios remuneracao spread taxa ipca cdi");
  if (q.includes("duration")) expansions.push("duration prazo medio vencimento resgate");
  return `${q} ${expansions.join(" ")}`;
}

function searchChunks(question, operationId, limit = 10) {
  const chunks = loadChunks();
  const expanded = expandQuestion(question);
  const tokens = expanded.split(/\s+/).filter((token) => token.length > 2);
  const aliases = OPERATIONS[operationId] || [];

  return chunks
    .map((chunk) => {
      const haystack = normalize(`${chunk.arquivo || ""} ${chunk.conteudo || ""}`);
      let score = 0;
      for (const token of tokens) {
        if (haystack.includes(token)) score += token.length > 5 ? 2 : 1;
      }
      for (const alias of aliases) {
        if (haystack.includes(normalize(alias))) score += 25;
      }
      return { ...chunk, score };
    })
    .filter((chunk) => chunk.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

function buildDocumentContext(chunks) {
  if (!chunks.length) return "Nenhum trecho relevante encontrado.";
  return chunks.map((chunk) => {
    const content = String(chunk.conteudo || "").slice(0, 2200);
    return `[Documento: ${chunk.arquivo || "Documento sem nome"} | Posicao: ${chunk.posicao ?? "N/A"}]\n${content}`;
  }).join("\n\n---\n\n");
}

async function callNvidia({ question, history, calcContext, docContext }) {
  if (!process.env.NVIDIA_API_KEY) {
    throw new Error("NVIDIA_API_KEY nao configurada no Vercel.");
  }

  const system = `Voce e o Assistente AXS, um assistente especializado em dividas, debentures, CRIs, contratos financeiros e documentos de emissao da AXS Energia.

Seu objetivo e ajudar o usuario a entender documentos e valores calculados do dashboard.

Regras:
1. Responda em portugues do Brasil, com linguagem clara, objetiva e util para a area financeira.
2. Para perguntas sobre PMT, PU, saldo, principal, datas de pagamento, juros, amortizacao, duration e vida media, use prioritariamente o CONTEXTO CALCULADO.
3. Para perguntas sobre garantias, clausulas, aditamentos, covenants, escritura, partes e vencimento antecipado, use os TRECHOS DOS DOCUMENTOS.
4. Nunca invente valores especificos. Se a informacao nao estiver no contexto, diga que nao encontrou.
5. Se usar documentos, cite o nome do documento quando possivel.
6. Nao use markdown pesado nem tabelas. Pode usar listas simples quando ajudar.
7. Se houver conflito entre documento e calculo, explique a diferenca e diga qual fonte esta usando.

CONTEXTO CALCULADO:
${calcContext}

TRECHOS DOS DOCUMENTOS:
${docContext}`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45000);

  let response;
  try {
    response = await fetch("https://integrate.api.nvidia.com/v1/chat/completions", {
      method: "POST",
      signal: controller.signal,
      headers: {
        Authorization: `Bearer ${process.env.NVIDIA_API_KEY}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        model: process.env.NVIDIA_MODEL || "google/gemma-4-31b-it",
        max_tokens: 1000,
        temperature: 0.2,
        top_p: 0.7,
        stream: false,
        messages: [
          { role: "system", content: system },
          ...history.slice(-10),
          { role: "user", content: question },
        ],
      }),
    });
  } finally {
    clearTimeout(timeout);
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(`Erro NVIDIA ${response.status}: ${JSON.stringify(data).slice(0, 800)}`);
  }
  return data?.choices?.[0]?.message?.content || "Sem resposta.";
}

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST") return res.status(405).json({ erro: "Metodo nao permitido. Use POST." });

  try {
    loadManifest();
    const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : (req.body || {});
    const { pergunta, historico = [] } = body;
    if (!pergunta || String(pergunta).trim().length < 1) {
      return res.status(400).json({ erro: "Pergunta muito curta." });
    }

    const operationId = detectOperation(pergunta);
    const variantId = detectVariant(operationId, pergunta);
    const payload = loadPayload(operationId, variantId);
    const chunks = searchChunks(pergunta, operationId, 7);
    const calcContext = buildCalculationContext(pergunta, payload);
    const docContext = buildDocumentContext(chunks);
    const resposta = await callNvidia({
      question: pergunta,
      history: historico,
      calcContext,
      docContext,
    });
    return res.status(200).json({ resposta });
  } catch (err) {
    console.error("Erro no /api/chat:", err);
    return res.status(500).json({ erro: err.message || "Erro ao consultar a IA." });
  }
};
