// node test_vortx_comparison.js — valores em oito casas, cobertura e proteção da API.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const C = require('./vortx-core.js');
const handler = require('./api/vortx.js');

async function run() {
  assert.equal(C.fixed('1e-8'), 1n);
  assert.equal(C.fixed('-0.000000005'), -1n);
  assert.equal(C.decimal(C.fixed('123.456789015')), '123.45678902');
  assert.equal(C.fixed(null), null);
  assert.equal(C.compare(null, 0).status, 'missing');
  assert.equal(C.compare('10.00499999', '10.00500000').status, 'different');
  assert.equal(C.compare('-10.00499999', '-10.00500000').status, 'different');
  assert.equal(C.compare('10.00000001', '10').status, 'cents');
  assert.equal(C.compare('10', '10').status, 'exact');
  assert.equal(C.decimal(C.compare('10.00000001', '10', '170000').impact), '0.00170000');
  assert.equal(C.format(-500000n, 2), '−0,01');
  const i = C.prepare({quantity: '100', local_as_of: '2026-10-30', local_rows: [{d: '2026-11-03', full: '10'}],
    reference: {history: [{d: '2026-11-03', full: '10'}], preview: [{d: '2026-11-03', full: '10'}]}});
  assert.equal(C.at(i, '2026-11-03').status, 'missing');
  assert.equal(C.at(i, '2026-11-03', 'full', 'preview').status, 'exact');
  assert.deepEqual(C.dates(i), []);
  const mapped = C.official({paymentDate: '2026-10-30T00:00:00Z', amortization: 75, ordinaryCashflowAmount: 5, extraordinaryAmortization: 70});
  assert.equal(mapped.ordinary, '5.00000000'); assert.equal(mapped.extra, '70.00000000'); assert.equal(mapped.full, null);
  const manifest = JSON.parse(fs.readFileSync('./data/vortx/manifest.json'));
  const instruments = manifest.instruments.map(i => C.prepare(JSON.parse(fs.readFileSync('./data/vortx/' + i.file))));
  const comparisons = instruments.map(i => C.at(i, manifest.local_as_of));
  assert.equal(comparisons.filter(r => r.status === 'exact').length, 1);
  assert.equal(comparisons.filter(r => ['exact', 'cents'].includes(r.status)).length, 14);
  assert.equal(comparisons.filter(r => r.status === 'different').length, 3);
  for (const i of instruments) {
    const r = C.at(i, manifest.local_as_of, 'empty');
    assert.notEqual(r.status, 'missing', i.code);
  }
  const oldTime = '2026-10-29T10:00:00Z';
  const reference = await handler.collect({code: 'PAXS12', operation_id: 97938}, {history: [{d: '2026-10-29'}], history_collected_at: oldTime}, async () => { throw new Error('offline'); });
  assert.equal(reference.history_collected_at, oldTime); assert.equal(reference.history.length, 1); assert.equal(reference.errors.length, 3);
  const res = () => ({headers: {}, setHeader(k, v) {this.headers[k] = v;}, status(code) {this.code = code; return this;}, json(body) {this.body = body; return this;}});
  let response = res(); await handler({method: 'POST', query: {}}, response); assert.equal(response.code, 405);
  response = res(); await handler({method: 'GET', query: {instrument: 'https://example.com/'}}, response); assert.equal(response.code, 400);
  response = res(); await handler({method: 'GET', query: {instrument: '../AXSC12'}}, response); assert.equal(response.code, 400);
  console.log('Conciliação: aritmética decimal, conceitos de fluxo, data-base, 17 instrumentos, cache e allowlist da API verificados.');
}
run().catch(error => {console.error(error); process.exitCode = 1;});
