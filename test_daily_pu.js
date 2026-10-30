// Regressão com as bases publicadas: nenhuma chamada a índices ou à Vórtx.
// Executar: node test_daily_pu.js
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const element = { addEventListener() {} };
const context = vm.createContext({
  window: {},
  document: {
    getElementById: () => element,
    querySelector: () => element,
    querySelectorAll: () => [],
  },
});
const source = fs.readFileSync(path.join(__dirname, "dashboard.js"), "utf8");
vm.runInContext(source.replace(/\nbootstrap\(\);\s*$/, ""), context);
vm.runInContext('state.activeDetailView = "daily_pu";', context);

const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, "data/operations.json"), "utf8"));
let views = 0;
let instruments = 0;
for (const operation of manifest.operations.filter((item) => item.id !== "geral")) {
  const payload = JSON.parse(fs.readFileSync(path.join(__dirname, "data/operations", `${operation.id}.json`), "utf8"));
  const before = JSON.stringify(payload);
  const selections = payload.variant_options?.length ? payload.variant_options.map((item) => item.id) : [""];
  for (const selected of selections) {
    const view = { ...payload, selected_variant: selected };
    const rows = context.getDailyPuSeries(view);
    assert.ok(rows.length, `${operation.id}/${selected}: histórico diário ausente`);
    assert.ok(context.getAvailableDetailViews(view).some((item) => item.id === "daily_pu"));
    const headers = context.getTableHeaders(view);
    const exported = context.getTableRowsForExport(view);
    assert.equal(exported.length, rows.length);
    assert.ok(exported.every((row) => row.length === headers.length), `${operation.id}/${selected}: colunas inconsistentes`);
    if (selected === "total") {
      const options = payload.variant_options.filter((item) => item.id !== "total");
      assert.equal(rows.length, options.reduce((total, option) => total + payload.variants[option.id].daily_pu_series.length, 0));
      for (const option of options) {
        const original = payload.variants[option.id].daily_pu_series;
        const actual = rows.filter((row) => row.instrument_label === option.label);
        assert.equal(JSON.stringify(actual.map((row) => [row.date, row.pu_cheio])), JSON.stringify(original.map((row) => [row.date, row.pu_cheio])));
      }
      for (let index = 1; index < rows.length; index++) {
        assert.ok(context.parseBrDate(rows[index].date) >= context.parseBrDate(rows[index - 1].date));
      }
    } else {
      const expected = selected ? payload.variants[selected].daily_pu_series : payload.daily_pu_series;
      assert.equal(JSON.stringify(rows), JSON.stringify(expected));
      instruments++;
    }
    if (rows.some((row) => String(row.sort_key || "").startsWith("daily-"))) {
      assert.match(context.getAvailableDetailViews(view).find((item) => item.id === "daily_pu").note, /interpolação/);
    }
    views++;
  }
  assert.equal(JSON.stringify(payload), before, `${operation.id}: base financeira alterada pela exibição`);
}
assert.equal(instruments, 17);
assert.equal(fs.readFileSync(path.join(__dirname, "docs/dashboard.js"), "utf8").replace(/\r\n/g, "\n"), source.replace(/\r\n/g, "\n"));
console.log(`PU diário validado em ${views} visões e ${instruments} instrumentos; valores preservados.`);
