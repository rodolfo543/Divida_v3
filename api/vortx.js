const fs = require('node:fs');
const path = require('node:path');
const catalog = require('../vortx_catalog.json');
const {official} = require('../vortx-core.js');
const BASE = 'https://apis.vortx.com.br/vxsite/api/operacao';
const cache = new Map();
const TERM_KEYS = ['ifCode', 'isinCode', 'issue', 'serie', 'firstIntegralizationDate', 'issueDate', 'issueDuty',
  'quantity', 'nominalUnitValue', 'totalVolume', 'interestRate', 'index', 'percentageIndex', 'periodoAmortizacao', 'periodoPagamentoJuros'];

async function collect(config, previous, fetcher = fetch) {
  const now = new Date().toISOString(), result = {collected_at: now, errors: [], cached: false};
  async function get(suffix) {
    const response = await fetcher(`${BASE}/${config.operation_id}${suffix}`, {
      headers: {'Accept': 'application/json', 'User-Agent': 'AXS-Debt-Comparison/1.0'}, signal: AbortSignal.timeout(18000)
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }
  await Promise.all(['history', 'preview', 'terms'].map(async key => {
    try {
      const raw = await get(key === 'history' ? '/preco-unitario/historico-pagamentos' : key === 'preview' ? '/preco-unitario/previa-pagamentos' : '');
      if (key === 'terms') {
        const operation = raw.operations?.[0]?.operation;
        if (!operation || operation.ifCode !== config.code) throw new Error('Código IF da ficha difere do cadastro');
        result.terms = Object.fromEntries(TERM_KEYS.map(name => [name, operation[name] ?? null]));
      } else {
        if (raw.success !== true || !Array.isArray(raw.unitPrices)) throw new Error('Resposta inválida da Vórtx');
        result[key] = raw.unitPrices.map(official).sort((a, b) => a.d.localeCompare(b.d));
        if (result[key].some(row => !/^\d{4}-\d{2}-\d{2}$/.test(row.d))) throw new Error('Data inválida');
      }
      result[key + '_collected_at'] = now;
    } catch (error) {
      result[key] = previous?.[key] || (key === 'terms' ? {} : []);
      result[key + '_collected_at'] = previous?.[key + '_collected_at'] || null;
      result.errors.push(`${key}: ${error.message}`);
      result.cached = true;
    }
  }));
  return result;
}

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'private, no-store');
  if (req.method !== 'GET') { res.setHeader('Allow', 'GET'); return res.status(405).json({error: 'Use GET'}); }
  const code = req.query?.instrument;
  const config = catalog.find(item => item.code === code);
  if (!config) return res.status(400).json({error: 'Instrumento não cadastrado'});
  try {
    const stored = cache.get(code);
    if (stored && Date.now() - stored.time < 5 * 60000) return res.status(200).json({...stored.reference, transport_cache: true});
    let previous = stored?.reference;
    if (!previous) {
      try { previous = JSON.parse(fs.readFileSync(path.join(__dirname, '../data/vortx/instruments', code + '.json'), 'utf8')).reference; }
      catch { previous = null; }
    }
    const reference = await collect(config, previous);
    cache.set(code, {time: Date.now(), reference});
    return res.status(200).json(reference);
  } catch {
    return res.status(502).json({error: 'Coleta indisponível. O último retrato publicado continua disponível na página.'});
  }
};
module.exports.collect = collect;
