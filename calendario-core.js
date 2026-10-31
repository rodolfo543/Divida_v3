(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CalendarCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  'use strict';
  const TYPES = {payment: 'Pagamento de PMT', incorporation: 'Incorporação de juros', maturity: 'Vencimento', recomposition: 'Recomposição de fundo · 1/6'};
  const months = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
  function cents(value) {
    if (value === null || value === undefined || value === '') return 0n;
    const m = String(value).match(/^(-?)(\d+)\.(\d{2})$/);
    if (!m) throw new Error('Valor monetário deve ter duas casas: ' + value);
    return (m[1] ? -1n : 1n) * (BigInt(m[2]) * 100n + BigInt(m[3]));
  }
  function cash(n) {
    const a = n < 0n ? -n : n;
    return (n < 0n ? '−' : '') + 'R$ ' + String(a / 100n).replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ',' + String(a % 100n).padStart(2, '0');
  }
  function sum(events, field = 'payment') {return events.reduce((total, event) => total + cents(event[field]), 0n);}
  function parse(d) {return new Date(d + 'T12:00:00Z');}
  function iso(d) {return d.toISOString().slice(0, 10);}
  function shift(d, days) {const x = parse(d); x.setUTCDate(x.getUTCDate() + days); return iso(x);}
  function monthKey(year, month) {return `${year}-${String(month + 1).padStart(2, '0')}`;}
  function monthDays(year, month) {
    const start = monthKey(year, month) + '-01', first = parse(start), offset = (first.getUTCDay() + 6) % 7;
    const days = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
    const count = Math.ceil((days + offset) / 7) * 7;
    return Array.from({length: count}, (_, i) => shift(start, i - offset));
  }
  function matches(event, operation, type) {
    return (!operation || event.operation === operation) && (!type || (type === 'payment' ? ['payment','maturity'].includes(event.type) : event.type === type));
  }
  function grouped(events) {
    const map = new Map();
    events.forEach(event => {if (!map.has(event.date)) map.set(event.date, []); map.get(event.date).push(event);});
    return map;
  }
  function withRecompositions(calendar, funding, referenceDay = 12) {
    if (funding.local_as_of !== calendar.local_as_of || funding.generated_at !== calendar.generated_at) throw new Error('As fontes de calendário e recomposição têm gerações diferentes.');
    if (!Number.isInteger(referenceDay) || referenceDay < 1 || referenceDay > 28) throw new Error('Dia de referência inválido.');
    const instruments = new Map(funding.instruments.map(i => [i.code, i]));
    const events = funding.contributions.map(row => {
      const instrument = instruments.get(row.code);
      if (!instrument?.eligible) throw new Error('Aporte sem instrumento aplicável: ' + row.code);
      return {id: `recomposition-${row.code}-${row.month}`, date: row.month + '-' + String(referenceDay).padStart(2,'0'),
        operation: row.operation, company: row.label, code: row.code, series: row.series, type: 'recomposition',
        title: TYPES.recomposition, payment: '0.00', interest: '0.00', amortization: '0.00', ordinary: '0.00',
        extra: '0.00', incorporation: '0.00', recomposition: row.amount, competence: row.month,
        target_payment_date: row.payment_date, target_payment: row.payment, installment: row.installment,
        planned_cumulative: row.planned_cumulative, reference_day: referenceDay, rank: row.rank, source_cycle_id: row.cycle_id,
        pending: row.pending, note: [instrument.note, row.pending ? instrument.review : ''].filter(Boolean).join(' ')};
    });
    const all = [...calendar.events.filter(e => e.type !== 'recomposition'), ...events].sort((a,b) => a.date.localeCompare(b.date) || a.company.localeCompare(b.company) || a.code.localeCompare(b.code) || a.id.localeCompare(b.id));
    if (new Set(all.map(e => e.id)).size !== all.length) throw new Error('Eventos duplicados na agenda.');
    return {...calendar, events: all, recomposition_count: events.length, recomposition_reference_day: referenceDay};
  }
  function escapeIcs(value) {return String(value ?? '').replace(/\\/g, '\\\\').replace(/\r?\n/g, '\\n').replace(/;/g, '\\;').replace(/,/g, '\\,');}
  function fold(line) {
    const lines = []; let part = '', length = 0;
    for (const char of line) {
      const bytes = new TextEncoder().encode(char).length;
      if (length + bytes > 75) {lines.push(part); part = ' '; length = 1;}
      part += char; length += bytes;
    }
    lines.push(part); return lines.join('\r\n');
  }
  function calendarFile(events, builtAt) {
    const stamp = new Date(builtAt).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
    const lines = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//AXS Energia//Agenda da divida//PT-BR','CALSCALE:GREGORIAN','METHOD:PUBLISH','X-WR-CALNAME:AXS Energia - Agenda da dívida'];
    for (const e of events) {
      const description = e.type === 'recomposition'
        ? `${e.company} · ${e.series} · ${e.code}\n${TYPES[e.type]}\nAporte planejado: ${cash(cents(e.recomposition))}\nCompetência: ${e.competence}\nParcela: ${e.installment}/6\nPMT alvo: ${e.target_payment_date} · ${cash(cents(e.target_payment))}\nDia ${e.reference_day}: referência de planejamento, não agendamento bancário. Não confirma transferência.\n${e.note || ''}`
        : `${e.company} · ${e.series} · ${e.code}\n${TYPES[e.type]}\nPMT: ${cash(cents(e.payment))}\nJuros pagos: ${cash(cents(e.interest))}\nAmortização: ${cash(cents(e.amortization))}\nIncorporação (sem caixa): ${cash(cents(e.incorporation))}\nCronograma do modelo; não confirma liquidação. Valores futuros sujeitos aos índices.\n${e.note || ''}`;
      lines.push('BEGIN:VEVENT', `UID:${e.id}@divida.axs`, `DTSTAMP:${stamp}`, `DTSTART;VALUE=DATE:${e.date.replace(/-/g, '')}`,
        `DTEND;VALUE=DATE:${shift(e.date, 1).replace(/-/g, '')}`, `SUMMARY:${escapeIcs(`${e.company} · ${e.series} · ${TYPES[e.type]}`)}`,
        `DESCRIPTION:${escapeIcs(description)}`, 'TRANSP:TRANSPARENT', 'STATUS:TENTATIVE','END:VEVENT');
    }
    lines.push('END:VCALENDAR'); return lines.map(fold).join('\r\n') + '\r\n';
  }
  return {TYPES, months, cents, cash, sum, parse, iso, shift, monthKey, monthDays, matches, grouped, withRecompositions, calendarFile};
});
