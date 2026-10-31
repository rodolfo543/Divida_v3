/* A referência é usada somente nesta página; os motores financeiros não importam este módulo. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.VortxCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const SCALE = 100000000n;
  const FIELDS = {
    full: 'PU cheio', empty: 'PU vazio (ex-evento)', nominal: 'Valor nominal', interest: 'Juros acumulados',
    paid_interest: 'Juros pagos / título', ordinary: 'Amortização ordinária / título',
    extra: 'Amortização extraordinária / título', incorporation: 'Incorporação / título', total: 'Pagamento total / título'
  };
  function divideRound(n, d) {
    if (d <= 0n) throw new Error('Divisor inválido');
    const sign = n < 0n ? -1n : 1n, a = n < 0n ? -n : n;
    return sign * (a / d + (a % d * 2n >= d ? 1n : 0n));
  }
  function fixed(value) {
    if (value === null || value === undefined || value === '') return null;
    const match = String(value).trim().match(/^([+-]?)(\d+)(?:\.(\d*))?(?:e([+-]?\d+))?$/i);
    if (!match) throw new Error('Número inválido: ' + value);
    const digits = BigInt(match[2] + (match[3] || ''));
    const power = 8 + Number(match[4] || 0) - (match[3] || '').length;
    if (Math.abs(power) > 100) throw new Error('Número fora da faixa');
    const magnitude = power >= 0 ? digits * 10n ** BigInt(power) : divideRound(digits, 10n ** BigInt(-power));
    return match[1] === '-' ? -magnitude : magnitude;
  }
  function decimal(n) {
    if (n === null) return null;
    const a = n < 0n ? -n : n;
    return (n < 0n ? '-' : '') + a / SCALE + '.' + String(a % SCALE).padStart(8, '0');
  }
  function format(n, places = 8, signed = false) {
    if (n === null || n === undefined) return '—';
    const rounded = divideRound(n, 10n ** BigInt(8 - places));
    const a = rounded < 0n ? -rounded : rounded, base = 10n ** BigInt(places);
    return (rounded < 0n ? '−' : signed && rounded > 0n ? '+' : '') + String(a / base).replace(/\B(?=(\d{3})+(?!\d))/g, '.') +
      (places ? ',' + String(a % base).padStart(places, '0') : '');
  }
  function compare(local, reference, quantity = '1') {
    const a = fixed(local), b = fixed(reference);
    if (a === null || b === null) return {local: a, reference: b, delta: null, impact: null, status: 'missing'};
    const delta = a - b, q = fixed(quantity);
    return {local: a, reference: b, delta, impact: q === null ? null : divideRound(delta * q, SCALE),
      status: a === b ? 'exact' : divideRound(a, 1000000n) === divideRound(b, 1000000n) ? 'cents' : 'different'};
  }
  function index(rows) { return new Map((rows || []).map(row => [row.d, row])); }
  function prepare(instrument) {
    instrument.localIndex = index(instrument.local_rows);
    instrument.historyIndex = index(instrument.reference.history);
    instrument.previewIndex = index(instrument.reference.preview);
    return instrument;
  }
  function at(instrument, day, field = 'full', mode = 'history') {
    const local = instrument.localIndex.get(day), reference = (mode === 'history' ? instrument.historyIndex : instrument.previewIndex).get(day);
    const result = compare(local && local[field], reference && reference[field], instrument.quantity);
    // O modelo estático não tem observações históricas além da sua data-base.
    if (mode === 'history' && day > instrument.local_as_of) return {...compare(null, reference && reference[field], instrument.quantity), projected: true};
    return result;
  }
  function dates(instrument, mode = 'history') {
    const ref = mode === 'history' ? instrument.historyIndex : instrument.previewIndex;
    if (mode === 'preview') return [...ref.keys()].sort();
    return [...new Set([...instrument.localIndex.keys(), ...ref.keys()])].filter(d => d <= instrument.local_as_of).sort();
  }
  function latestComparableDay(instruments, cutoff) {
    let latest = null;
    for (const instrument of instruments) for (const [d, reference] of instrument.historyIndex) {
      if (d > cutoff || d > instrument.local_as_of || (latest && d <= latest)) continue;
      const local = instrument.localIndex.get(d);
      if (local?.full != null && reference.full != null) latest = d;
    }
    return latest;
  }
  function official(row) {
    const names = {full: 'unitPriceFull', empty: 'unitPriceEmpty', nominal: 'nominalValue', interest: 'interestValue',
      paid_interest: 'interestCashflowAmount', ordinary: 'ordinaryCashflowAmount', extra: 'extraordinaryAmortization',
      incorporation: 'incorporationCashflowAmount', total: 'total'};
    return Object.fromEntries([['d', String(row.paymentDate).slice(0, 10)], ...Object.entries(names).map(([a, b]) => [a, decimal(fixed(row[b]))])]);
  }
  return {SCALE, FIELDS, fixed, decimal, format, divideRound, compare, index, prepare, at, dates, latestComparableDay, official};
});
