/* Página de conferência: nenhuma escrita nos cálculos ou nos dados da carteira. */
'use strict';
const C = window.VortxCore;
const $ = id => document.getElementById(id);
const state = {manifest: null, instruments: [], active: null, mode: 'history', page: 0, rows: []};
const labels = {exact: 'Igual nas 8 casas', cents: 'Igual em centavos', different: 'Divergência em centavos', missing: 'Sem par de dados'};
const eventFields = ['paid_interest', 'ordinary', 'extra', 'incorporation', 'total'];
const abs = n => n < 0n ? -n : n;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const day = value => /^\d{4}-\d{2}-\d{2}/.test(value || '') ? value.slice(0, 10).split('-').reverse().join('/') : '—';
const stamp = value => value ? new Date(value).toLocaleString('pt-BR', {timeZone: 'America/Sao_Paulo'}) : 'Sem coleta válida';
const tag = status => `<span class="status-tag ${status}">${labels[status]}</span>`;
const pu = n => C.format(n);
const money = (n, signed = false) => n === null ? '—' : 'R$ ' + C.format(n, 2, signed);
const blocked = i => i.pending || i.local_method === 'estimated';
function latest(rows) { return rows?.length ? rows[rows.length - 1].d : null; }
function oldest(rows) { return rows?.length ? rows[0].d : null; }
function shiftDate(d, amount) { const a = new Date(d + 'T12:00:00Z'); a.setUTCDate(a.getUTCDate() + amount); return a.toISOString().slice(0, 10); }
function deltaClass(result) { return result.status === 'different' ? 'delta-alert' : 'delta-small'; }
function request(path) { return fetch(path, {cache: 'no-cache'}).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }); }

function overview() {
  const date = $('asOf').value;
  const all = state.instruments.map(i => ({i, result: C.at(i, date)}));
  const counts = name => all.filter(r => r.result.status === name).length;
  const exact = counts('exact'), cents = counts('cents') + exact, missing = counts('missing');
  const metrics = [
    ['Instrumentos acompanhados', all.length, '17 instrumentos · 13 operações', ''],
    ['Iguais nas 8 casas', exact, 'PU cheio sem diferença na data', 'mint'],
    ['Coincidem em centavos', cents, `${counts('cents')} com resíduo · inclui os exatos`, 'blue'],
    ['Divergem em centavos', counts('different'), `${all.filter(r => r.i.pending).length} pendências documentadas na carteira`, 'amber'],
    ['Sem par na data', missing, 'Exige o mesmo dia nas duas fontes', missing ? 'amber' : '']
  ];
  $('metrics').innerHTML = metrics.map(([a, b, c, color]) => `<article class="cmp-metric"><span class="metric-label">${a}</span><strong class="${color}">${b}</strong><p>${c}</p></article>`).join('');
  const include = $('includePending').checked;
  const scoped = all.filter(r => r.result.impact !== null && (include || !blocked(r.i)));
  const net = scoped.reduce((n, r) => n + r.result.impact, 0n), gross = scoped.reduce((n, r) => n + abs(r.result.impact), 0n);
  $('impactStrip').innerHTML = `<p>Diferença líquida de saldo<strong>${money(net, true)}</strong></p><p>Soma absoluta das diferenças<strong>${money(gross)}</strong></p><p class="impact-scope">${scoped.length} instrumentos com par na data. ${include ? 'Inclui pendências e séries estimadas.' : 'Exclui as 3 pendências documentadas, incluindo as 2 séries estimadas da AXS 05.'}<br>Data-base: ${day(date)} · sinal = cálculo AXS − Vórtx.</p>`;
  const query = $('search').value.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const filter = $('statusFilter').value;
  const rows = all.filter(({i, result}) => {
    const text = `${i.label} ${i.code} ${i.series}`.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    return text.includes(query) && (filter === 'all' || filter === 'pending' && i.pending || filter === 'cents' && ['cents', 'exact'].includes(result.status) || filter === result.status);
  }).sort((a, b) => { const x = abs(a.result.impact ?? 0n), y = abs(b.result.impact ?? 0n); return x > y ? -1 : x < y ? 1 : a.i.code.localeCompare(b.i.code); });
  $('rowCount').textContent = `${rows.length} de ${all.length} instrumentos`;
  $('overviewRows').innerHTML = rows.map(({i, result: r}) => `<tr><td><strong>${esc(i.label)} · ${esc(i.series)}</strong><small>${esc(i.code)}${i.local_method === 'estimated' ? ' · PU diário estimado' : ''}</small></td><td>${pu(r.local)}</td><td>${pu(r.reference)}</td><td class="${deltaClass(r)}">${C.format(r.delta, 8, true)}</td><td class="${deltaClass(r)}">${money(r.impact, true)}</td><td>${tag(r.status)}${i.pending ? '<div class="pending-line"><span class="status-tag pending">Pendência documentada</span></div>' : ''}</td><td><button class="row-action" type="button" data-instrument="${esc(i.code)}" aria-label="Detalhar ${esc(i.code)}">Detalhar ↗</button></td></tr>`).join('') || '<tr><td colspan="7" class="empty-cell">Nenhum instrumento corresponde aos filtros.</td></tr>';
  state.overviewRows = rows;
}

function selectInstrument(code, scroll = false) {
  state.active = state.instruments.find(i => i.code === code) || state.instruments[0];
  $('instrumentSelect').value = state.active.code;
  const i = state.active;
  $('detailTitle').textContent = `${i.label} · ${i.series}`;
  $('reviewNote').classList.toggle('pending', !!i.pending);
  $('reviewNote').innerHTML = `${i.pending ? '<strong>Pendência documentada.</strong> ' : ''}${esc(i.review)}${i.local_method === 'estimated' ? '<br>Os valores diários estimados não constituem validação do motor contratual. Fluxos e incorporações locais indisponíveis para conciliação nessa série estimada.' : ''}`;
  setRange();
  renderDetail();
  if (scroll) $('detail').scrollIntoView({behavior: 'smooth', block: 'start'});
}
function setRange(all = false) {
  const dates = C.dates(state.active, state.mode), end = state.mode === 'history' ? $('asOf').value : dates.at(-1);
  $('dateTo').value = end || state.active.local_as_of;
  $('dateFrom').value = all ? dates[0] || $('dateTo').value : state.mode === 'preview' ? dates[0] || $('dateTo').value : shiftDate($('dateTo').value, -90);
  $('breakdownDay').value = $('dateTo').value;
  state.page = 0;
}
function filteredDates() {
  const from = $('dateFrom').value, to = $('dateTo').value;
  return C.dates(state.active, state.mode).filter(d => (!from || d >= from) && (!to || d <= to));
}
function renderDetail() {
  const i = state.active, field = $('component').value, dates = filteredDates();
  const rows = dates.map(d => ({d, ...C.at(i, d, field, state.mode)}));
  state.rows = rows;
  const paired = rows.filter(r => r.delta !== null), missing = rows.length - paired.length;
  const exact = paired.filter(r => r.status === 'exact').length;
  const biggest = paired.reduce((a, b) => a === null || abs(b.delta) > abs(a.delta) ? b : a, null);
  const reference = state.mode === 'history' ? i.reference.history : i.reference.preview;
  const cards = [
    ['Datas com par no período', String(paired.length), `${missing} sem par de dados`],
    [state.mode === 'history' ? 'Iguais nas 8 casas' : 'Projeções coincidentes', String(exact), state.mode === 'history' ? `${paired.filter(r => r.status !== 'different').length} coincidem em centavos` : 'Coincidência indicativa, sem validação histórica'],
    ['Maior diferença por título', biggest ? C.format(biggest.delta, 8, true) : '—', biggest ? day(biggest.d) : 'Sem comparação no período'],
    ['Cobertura da Vórtx', reference.length ? `${day(oldest(reference))} →` : 'Sem dados', reference.length ? day(latest(reference)) : 'Nenhum valor publicado']
  ];
  $('coverage').innerHTML = cards.map(([a, b, c]) => `<div class="coverage-item"><span>${a}</span><strong>${b}</strong><small>${c}</small></div>`).join('');
  $('chartTitle').textContent = `${C.FIELDS[field]} · R$ por título`;
  drawChart(rows, false); drawChart(rows, true);
  $('historyTitle').textContent = `${state.mode === 'history' ? 'Comparação diária' : 'Comparação das prévias'} · ${C.FIELDS[field]}`;
  renderPage(); renderBreakdown(); renderEvents(dates); renderSources();
}
function renderPage() {
  const rows = [...state.rows].reverse(), count = Math.max(1, Math.ceil(rows.length / 30));
  state.page = Math.max(0, Math.min(state.page, count - 1));
  const part = rows.slice(state.page * 30, (state.page + 1) * 30);
  $('dailyRows').innerHTML = part.map(r => `<tr><td>${day(r.d)}</td><td>${pu(r.local)}</td><td>${pu(r.reference)}</td><td class="${deltaClass(r)}">${C.format(r.delta, 8, true)}</td><td>${money(r.impact, true)}</td><td>${state.mode === 'preview' && r.status !== 'missing' ? '<span class="status-tag">Prévia · ' + labels[r.status].toLowerCase() + '</span>' : tag(r.status)}</td><td><button class="row-action" type="button" data-day="${r.d}" aria-label="Ver composição em ${day(r.d)}">Composição</button></td></tr>`).join('') || '<tr><td colspan="7" class="empty-cell">Não há datas neste intervalo. Ajuste o período ou selecione “Todo o período”.</td></tr>';
  $('pageLabel').textContent = `${rows.length} datas · ${state.page + 1} / ${count}`;
  $('previousPage').disabled = state.page === 0; $('nextPage').disabled = state.page + 1 === count;
}
function renderBreakdown() {
  const d = $('breakdownDay').value, i = state.active;
  $('breakdownDate').textContent = day(d);
  $('breakdownRows').innerHTML = Object.entries(C.FIELDS).map(([field, label]) => {
    const r = C.at(i, d, field, state.mode);
    return `<tr><td>${label}</td><td>${pu(r.local)}</td><td>${pu(r.reference)}</td><td class="${deltaClass(r)}">${C.format(r.delta, 8, true)}</td><td>${state.mode === 'preview' && r.status !== 'missing' ? '<span class="status-tag">Prévia</span>' : tag(r.status)}</td></tr>`;
  }).join('');
}
function renderEvents(dates) {
  const i = state.active, ref = state.mode === 'history' ? i.historyIndex : i.previewIndex;
  const events = dates.filter(d => eventFields.some(f => [i.localIndex.get(d)?.[f], ref.get(d)?.[f]].some(v => v != null && C.fixed(v) !== 0n)));
  $('eventCount').textContent = `${events.length} datas no período${events.length > 200 ? ' · exibindo as 200 mais recentes; CSV contém todas' : ''}`;
  $('eventRows').innerHTML = [...events].reverse().slice(0, 200).map(d => `<tr><td>${day(d)}</td>${eventFields.map(f => {
    const r = C.at(i, d, f, state.mode);
    return `<td><span>${pu(r.local)} / ${pu(r.reference)}</span><small class="${deltaClass(r)}">Δ ${C.format(r.delta, 8, true)}</small></td>`;
  }).join('')}</tr>`).join('') || '<tr><td colspan="6" class="empty-cell">Nenhum evento de caixa ou incorporação registrado neste período.</td></tr>';
}

function drawChart(rows, delta) {
  const host = $(delta ? 'deltaChart' : 'comparisonChart');
  const values = rows.flatMap(r => delta ? r.delta === null ? [] : [Number(r.delta) / 1e8] : [r.local, r.reference].filter(v => v !== null).map(v => Number(v) / 1e8));
  if (!rows.length || !values.length) { host.innerHTML = '<p class="chart-empty">Sem dados suficientes para o gráfico neste período.</p>'; return; }
  const W = 1120, H = delta ? 130 : 240, L = delta ? 120 : 85, R = 24, T = 20, B = 30;
  let min = Math.min(...values), max = Math.max(...values);
  if (delta) { min = Math.min(0, min); max = Math.max(0, max); }
  const pad = (max - min) * .13 || (delta ? .00000001 : .01); min -= pad; max += pad;
  const x = idx => L + idx / Math.max(1, rows.length - 1) * (W - L - R), y = v => T + (max - v) / (max - min) * (H - T - B);
  const axisFormat = v => v.toLocaleString('pt-BR', {minimumFractionDigits: delta ? 6 : 2, maximumFractionDigits: delta ? 8 : 2});
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${delta ? 'Diferença por título: cálculo AXS menos Vórtx' : esc(C.FIELDS[$('component').value]) + ': cálculo AXS e Vórtx'} no período selecionado"><title>${delta ? 'Diferença por título (R$)' : esc(C.FIELDS[$('component').value])}</title>`;
  for (let j = 0; j <= (delta ? 2 : 3); j++) {
    const value = min + (max - min) * j / (delta ? 2 : 3), py = y(value);
    svg += `<line x1="${L}" x2="${W - R}" y1="${py}" y2="${py}" stroke="#ffffff0e"/><text x="${L - 10}" y="${py + 4}" text-anchor="end" fill="#97adc2" font-size="10">${axisFormat(value)}</text>`;
  }
  if (delta) svg += `<line x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}" stroke="#ffcb9044" stroke-dasharray="4 4"/>`;
  for (const [field, color] of delta ? [['delta', '#ffcb90']] : [['local', '#73f0c5'], ['reference', '#82b5ff']]) {
    let path = '', open = false;
    rows.forEach((row, idx) => {
      if (row[field] === null) { open = false; return; }
      path += `${open ? 'L' : 'M'}${x(idx).toFixed(2)},${y(Number(row[field]) / 1e8).toFixed(2)} `; open = true;
    });
    svg += `<path d="${path}" fill="none" stroke="${color}" stroke-width="${delta ? 1.8 : 2}" ${field === 'reference' ? 'stroke-dasharray="5 3"' : ''}/>`;
    if (rows.length === 1 && rows[0][field] !== null) svg += `<circle cx="${x(0)}" cy="${y(Number(rows[0][field]) / 1e8)}" r="3" fill="${color}"/>`;
  }
  const ticks = [...new Set([0, Math.floor((rows.length - 1) / 2), rows.length - 1])];
  ticks.forEach(idx => { svg += `<text x="${x(idx)}" y="${H - 8}" text-anchor="${idx === 0 ? 'start' : idx === rows.length - 1 ? 'end' : 'middle'}" fill="#97adc2" font-size="10">${day(rows[idx].d)}</text>`; });
  if (delta) svg += `<text x="${L}" y="12" fill="#ffcb90" font-size="10">Δ por título · AXS − Vórtx</text>`;
  host.innerHTML = svg + '</svg>';
}

function renderSources() {
  const i = state.active, r = i.reference, terms = r.terms || {}, base = `https://apis.vortx.com.br/vxsite/api/operacao/${i.operation_id}`;
  const errors = r.errors?.length ? `<p class="source-error">Coleta parcial ou indisponível: ${esc(r.errors.join(' · '))}. Os dados preservados mantêm a data da última coleta válida.</p>` : '';
  const defined = value => value === undefined || value === null ? '—' : esc(value);
  $('sourceContent').innerHTML = `<div class="source-grid"><article class="source-block"><h3>Cálculo AXS · ${esc(i.code)}</h3><dl><dt>Data-base do modelo</dt><dd>${day(i.local_as_of)}</dd><dt>Geração local</dt><dd>${esc(i.local_generated_at || state.manifest.local_generated_at)}</dd><dt>Quantidade do modelo</dt><dd>${C.format(C.fixed(i.quantity), 0)} títulos</dd><dt>Série diária</dt><dd>${i.local_method === 'estimated' ? 'Estimada por interpolação · pendente de conciliação' : 'Calculada pelo modelo independente'}</dd><dt>Origem</dt><dd>Arquivo publicado da operação ${esc(i.operation)}${i.variant ? ' · ' + esc(i.variant) : ''}</dd><dt>SHA-256 da origem</dt><dd class="digest">${esc(i.local_source_sha256)}</dd></dl><div class="source-links"><a href="./index.html">Abrir área de cálculos ↗</a><a href="./data/vortx/instruments/${i.code}.json" target="_blank" rel="noopener">Retrato da comparação JSON ↗</a></div></article><article class="source-block"><h3>Referência Vórtx · operação ${i.operation_id}</h3><dl><dt>Histórico coletado</dt><dd>${stamp(r.history_collected_at)}</dd><dt>Prévia coletada</dt><dd>${stamp(r.preview_collected_at)}</dd><dt>Ficha coletada</dt><dd>${stamp(r.terms_collected_at)}</dd><dt>Taxa na ficha</dt><dd>${defined(terms.interestRate)}% a.a. · conferir vigência contratual</dd><dt>1ª integralização</dt><dd>${day(terms.firstIntegralizationDate)}</dd><dt>Vencimento</dt><dd>${day(terms.issueDuty)}</dd><dt>Quantidade na ficha</dt><dd>${terms.quantity != null ? C.format(C.fixed(terms.quantity), 0) : '—'} títulos</dd><dt>Juros / amortização</dt><dd>${defined(terms.periodoPagamentoJuros)} / ${defined(terms.periodoAmortizacao)}</dd></dl>${errors}<div class="source-links"><a href="https://www.vortx.com.br/investidor/dcm/operacao?id=${i.operation_id}&page=2" target="_blank" rel="noopener">Página Vórtx ↗</a><a href="https://apis.vortx.com.br/vxsite/api/operacao/${i.code}/memoria-de-calculo" target="_blank" rel="noopener">Baixar memória de cálculo ↓</a><a href="${base}/preco-unitario/historico-pagamentos" target="_blank" rel="noopener">API do histórico ↗</a><a href="${base}/preco-unitario/previa-pagamentos" target="_blank" rel="noopener">API da prévia ↗</a></div></article></div>`;
}
function downloadCsv(filename, rows) {
  const content = '\ufeff' + rows.map(row => row.map(v => '"' + String(v ?? '').replace(/"/g, '""') + '"').join(';')).join('\r\n');
  const url = URL.createObjectURL(new Blob([content], {type: 'text/csv;charset=utf-8'})), a = document.createElement('a');
  a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function csvNumber(value) { return value === null ? '' : C.decimal(value).replace('.', ','); }
function exportOverview() {
  const header = ['Data', 'Empresa', 'Série', 'IF', 'PU AXS', 'PU Vórtx', 'Delta PU AXS menos Vórtx', 'Quantidade do modelo', 'Impacto R$', 'Situação', 'Pendência', 'Método diário', 'Histórico Vórtx coletado'];
  downloadCsv(`conciliacao-vortx-${$('asOf').value}.csv`, [header, ...state.overviewRows.map(({i, result: r}) => [$('asOf').value, i.label, i.series, i.code, csvNumber(r.local), csvNumber(r.reference), csvNumber(r.delta), i.quantity.replace('.', ','), csvNumber(r.impact), labels[r.status], i.pending ? 'Sim' : 'Não', i.local_method, i.reference.history_collected_at])]);
}
function exportDetail() {
  const i = state.active;
  const headers = ['Data', 'IF', 'Modo', 'Quantidade do modelo', 'Coleta Vórtx', ...Object.values(C.FIELDS).flatMap(label => [label + ' AXS', label + ' Vórtx', label + ' delta', label + ' impacto R$', label + ' situação'])];
  const rows = filteredDates().map(d => [d, i.code, state.mode === 'history' ? 'Histórico' : 'Prévia', i.quantity.replace('.', ','), i.reference[state.mode + '_collected_at'], ...Object.keys(C.FIELDS).flatMap(f => {
    const r = C.at(i, d, f, state.mode); return [csvNumber(r.local), csvNumber(r.reference), csvNumber(r.delta), csvNumber(r.impact), labels[r.status]];
  })]);
  downloadCsv(`conciliacao-${i.code}-${state.mode}-${$('dateFrom').value}-${$('dateTo').value}.csv`, [headers, ...rows]);
}
async function refresh() {
  const button = $('refreshVortx'); button.disabled = true;
  let done = 0, failures = 0, cursor = 0;
  const worker = async () => {
    while (cursor < state.instruments.length) {
      const i = state.instruments[cursor++];
      try {
        const reference = await request(`./api/vortx?instrument=${encodeURIComponent(i.code)}`);
        if (!Array.isArray(reference.history) || !Array.isArray(reference.preview)) throw new Error('Resposta incompleta');
        if (reference.errors?.length) failures++;
        C.prepare(Object.assign(i, {reference}));
      } catch (error) { failures++; i.reference.errors = [`Atualização ao vivo falhou (${error.message}); retrato anterior preservado.`]; }
      done++; $('loadStatus').textContent = `Atualizando Vórtx: ${done} de ${state.instruments.length} instrumentos…`;
    }
  };
  await Promise.all([worker(), worker()]);
  overview(); renderDetail(); updateStatus(failures); button.disabled = false;
}
function updateStatus(failures) {
  const dates = state.instruments.map(i => i.reference.history_collected_at).filter(Boolean).sort();
  $('loadStatus').classList.toggle('error', failures > 0);
  $('loadStatus').textContent = `Cálculo local: ${state.manifest.local_generated_at} · Histórico Vórtx coletado de ${stamp(dates[0])} a ${stamp(dates.at(-1))} (Brasília). ${failures ? `${failures} instrumento(s) com falha ou coleta parcial; consulte as fontes.` : 'Referências carregadas para os 17 instrumentos.'} Atualizar Vórtx não recalcula a dívida. Cache de consulta: até 5 minutos.`;
}
async function bootstrap() {
  try {
    state.manifest = await request('./data/vortx/manifest.json');
    const pending = [...state.manifest.instruments]; let cursor = 0;
    const worker = async () => { while (cursor < pending.length) { const item = pending[cursor++]; state.instruments.push(C.prepare(await request('./data/vortx/' + item.file))); } };
    await Promise.all([worker(), worker(), worker()]);
    state.instruments.sort((a, b) => state.manifest.instruments.findIndex(i => i.code === a.code) - state.manifest.instruments.findIndex(i => i.code === b.code));
    // Em fins de semana ou antes da publicação diária, iniciar na última data
    // que de fato tenha PU calculado e referência publicada no mesmo dia.
    $('asOf').value = C.latestComparableDay(state.instruments, state.manifest.local_as_of) || state.manifest.local_as_of;
    $('asOf').max = state.manifest.local_as_of;
    $('asOf').min = state.instruments.flatMap(i => i.local_rows.map(r => r.d)).sort()[0];
    $('instrumentSelect').innerHTML = state.instruments.map(i => `<option value="${i.code}">${esc(i.label)} · ${esc(i.series)} · ${i.code}</option>`).join('');
    $('component').innerHTML = Object.entries(C.FIELDS).map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
    $('comparisonContent').hidden = false; $('refreshVortx').disabled = false;
    overview(); selectInstrument(new URLSearchParams(location.search).get('instrument') || 'PAXS12');
    updateStatus(state.instruments.filter(i => i.reference.errors?.length).length);
  } catch (error) {
    $('loadStatus').classList.add('error');
    $('loadStatus').textContent = `Não foi possível carregar a comparação (${error.message}). Recarregue a página; a área de cálculos permanece disponível pelo menu.`;
  }
}
$('search').addEventListener('input', overview);
for (const id of ['statusFilter', 'includePending']) $(id).addEventListener('change', overview);
$('asOf').addEventListener('change', () => {
  if (!$('asOf').value || $('asOf').value > state.manifest.local_as_of) $('asOf').value = state.manifest.local_as_of;
  overview(); if (state.mode === 'history') { setRange(); renderDetail(); }
});
$('overviewRows').addEventListener('click', e => { const button = e.target.closest('[data-instrument]'); if (button) selectInstrument(button.dataset.instrument, true); });
$('instrumentSelect').addEventListener('change', e => selectInstrument(e.target.value));
for (const id of ['component', 'dateFrom', 'dateTo']) $(id).addEventListener('change', () => { state.page = 0; renderDetail(); });
$('allHistory').addEventListener('click', () => { setRange(true); renderDetail(); });
$('breakdownDay').addEventListener('change', renderBreakdown);
$('dailyRows').addEventListener('click', e => { const button = e.target.closest('[data-day]'); if (button) { $('breakdownDay').value = button.dataset.day; renderBreakdown(); document.querySelector('.component-breakdown').scrollIntoView({behavior: 'smooth', block: 'start'}); } });
$('previousPage').addEventListener('click', () => { state.page--; renderPage(); });
$('nextPage').addEventListener('click', () => { state.page++; renderPage(); });
for (const [id, mode] of [['historyTab', 'history'], ['previewTab', 'preview']]) $(id).addEventListener('click', () => {
  state.mode = mode;
  $('historyTab').setAttribute('aria-selected', String(mode === 'history')); $('previewTab').setAttribute('aria-selected', String(mode === 'preview'));
  $('detailContent').setAttribute('aria-labelledby', id); $('previewNotice').hidden = mode !== 'preview'; setRange(); renderDetail();
});
$('exportOverview').addEventListener('click', exportOverview); $('exportDetail').addEventListener('click', exportDetail);
$('refreshVortx').addEventListener('click', refresh);
bootstrap();
