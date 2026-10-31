'use strict';
const U=window.FinanceUI,K=window.CalendarCore,$=id=>document.getElementById(id);
const state={data:null,month:'',operation:'',code:'AXS811',visible:[]};
function shift(m,n){const [y,a]=m.split('-').map(Number),d=new Date(Date.UTC(y,a-1+n,1));return d.toISOString().slice(0,7);}
function scoped(){return state.data.instruments.filter(i=>!state.operation||i.operation===state.operation);}
function items(month){return state.data.contributions.filter(i=>i.month===month&&(!state.operation||i.operation===state.operation));}
function position(i){const row=state.data.contributions.find(r=>r.code===i.code&&r.month===state.month);const cycle=i.cycles.find(c=>c.start_month<=state.month&&c.end_month>=state.month)||i.cycles.find(c=>c.start_month>state.month)||i.cycles.at(-1);return {i,row,cycle,status:row?'active':state.month<i.start_month?'waiting':'ended'};}
function render(){
  state.month=$('fundMonth').value;state.operation=$('fundCompany').value;
  const contributions=items(state.month),eligible=scoped().filter(i=>i.eligible),active=new Set(contributions.map(r=>r.code)),waiting=eligible.filter(i=>state.month<i.start_month),sub=contributions.filter(r=>r.rank==='Subordinada');
  const metrics=[['Aporte planejado no mês',K.cash(K.sum(contributions,'amount')),'1/6 das PMTs em composição'],['Instrumentos em composição',String(active.size),`${eligible.length} aplicáveis nos filtros`],['Referência subordinada',K.cash(K.sum(sub,'amount')),'Incluída no total; sujeita à cascata'],['Ainda em carência',String(waiting.length),'Composição começa seis meses antes da primeira amortização']];
  $('fundMetrics').innerHTML=metrics.map(([a,b,c])=>`<article class="finance-metric"><span>${a}</span><strong>${b}</strong><small>${c}</small></article>`).join('');
  const filter=$('fundFilter').value,rows=eligible.map(position).filter(r=>filter==='all'||r.status===filter);
  state.visible=rows;$('fundCount').textContent=`${rows.length} instrumentos · ${U.month(state.month)}`;
  $('fundRows').innerHTML=rows.map(({i,row,cycle,status})=>`<tr><td><strong>${U.esc(i.label)} · ${U.esc(i.series)}</strong><small>${U.esc(i.code)} · ${U.esc(i.rank)}${i.pending?' · pendência de PU':''}</small></td><td>${U.day(cycle?.payment_date)}</td><td>${cycle?K.cash(K.cents(cycle.payment)):'—'}</td><td><strong>${row?K.cash(K.cents(row.amount)):K.cash(0n)}</strong>${row?`<small>Parcela ${row.installment}/6</small>`:''}</td><td><span class="finance-tag ${status==='active'?'active':''}">${status==='active'?'Em composição':status==='waiting'?'Início em '+U.month(i.start_month):'Ciclo encerrado'}</span></td><td><button type="button" class="finance-link-button" data-fund="${i.code}">Detalhar ↗</button></td></tr>`).join('')||'<tr><td colspan="6" class="empty-cell">Nenhum instrumento aplicável nestes filtros. Consulte abaixo o tratamento das operações fora do rateio.</td></tr>';
  $('fundExcluded').innerHTML=scoped().filter(i=>!i.eligible).map(i=>`<tr><td><strong>${U.esc(i.label)} · ${U.esc(i.series)}</strong><small>${i.code}</small></td><td style="white-space:normal;text-align:left">${U.esc(i.reason)}</td></tr>`).join('')||'<tr><td colspan="2" class="empty-cell">Todas as operações selecionadas possuem regra de composição.</td></tr>';
  const options=eligible;
  $('fundInstrument').innerHTML=options.map(i=>`<option value="${i.code}">${U.esc(i.label)} · ${U.esc(i.series)} · ${i.code}</option>`).join('');
  if(!options.some(i=>i.code===state.code))state.code=options.find(i=>active.has(i.code))?.code||options[0]?.code||'';
  $('fundInstrument').disabled=!options.length;
  $('fundInstrument').value=state.code;renderDetail();renderProjection();
}
function renderDetail(){
  const i=state.data.instruments.find(i=>i.code===state.code);
  if(!i){$('fundReview').innerHTML='<div class="finance-callout">A empresa selecionada não possui instrumento aplicável ao rateio de 1/6. Consulte o tratamento na tabela de operações fora do rateio.</div>';$('fundDefinition').innerHTML='';$('fundInstallments').innerHTML='';$('fundSource').textContent='';$('fundDocuments').hidden=true;return;}
  $('fundDocuments').hidden=false;
  const {cycle,row}=position(i);
  const notes=[i.note,i.pending?i.review:''].filter(Boolean);
  $('fundReview').innerHTML=notes.length?`<div class="finance-callout ${i.pending?'pending':''}">${notes.map(U.esc).join('<br>')}</div>`:'';
  $('fundDefinition').innerHTML=`<dt>Instrumento</dt><dd>${i.code} · ${U.esc(i.rank)}</dd><dt>PMT projetada</dt><dd>${K.cash(K.cents(cycle.payment))} · ${U.day(cycle.payment_date)}</dd><dt>Referência de 1/6</dt><dd>${K.cash(K.cents(cycle.one_sixth))}</dd><dt>Janela de composição</dt><dd>${U.month(cycle.start_month)} a ${U.month(cycle.end_month)}</dd><dt>Aporte na competência</dt><dd>${row?K.cash(K.cents(row.amount)):K.cash(0n)}</dd><dt>Acumulado programado</dt><dd>${row?K.cash(K.cents(row.planned_cumulative)):'Competência fora deste ciclo'}</dd>${i.verification_day?`<dt>Verificação contratual</dt><dd>Dia ${i.verification_day} · referência do contrato, não agendamento bancário</dd>`:''}`;
  $('fundInstallments').innerHTML=cycle.installments.map(p=>`<div class="installment ${p.month===state.month?'selected':''}"><span>${U.month(p.month)}</span><strong>${K.cash(K.cents(p.amount))}</strong><small>Parcela ${p.installment}/6</small></div>`).join('');
  $('fundSource').textContent=`Fonte: ${i.source}. Cláusulas ${i.clauses}. Páginas ${i.pages}. Encerramento: ${i.end==='penultimate'?'até a PMT penúltima, conforme o contrato':'até a última PMT do fluxo'}. Valores do modelo de ${state.data.generated_at}.`;
  $('fundDocuments').href='./documentos.html?operation='+encodeURIComponent(i.operation);
}
function renderProjection(){
  const rows=Array.from({length:12},(_,n)=>{const month=shift(state.month,n),v=items(month);return {month,total:K.sum(v,'amount'),count:new Set(v.map(r=>r.code)).size};});
  const max=rows.reduce((a,r)=>r.total>a?r.total:a,1n);
  $('fundChart').innerHTML=rows.map(r=>`<button type="button" class="projection-column ${r.month===state.month?'selected':''}" data-month="${r.month}" aria-label="${U.month(r.month)}: ${K.cash(r.total)}"><span>${K.cash(r.total)}</span><i style="height:${Math.max(3,Number(r.total*115n/max))}px"></i><small>${U.month(r.month)}</small></button>`).join('');
  $('fundProjection').innerHTML=rows.map(r=>`<tr><td><button type="button" class="finance-link-button" data-month="${r.month}">${U.month(r.month)}</button></td><td>${K.cash(r.total)}</td><td>${r.count}</td></tr>`).join('');
}
async function load(){try{
  state.data=await U.json('./data/recomposition.json');const d=state.data;
  $('fundMonth').value=d.local_as_of.slice(0,7);$('fundMonth').min=d.contributions[0].month;$('fundMonth').max=d.contributions.at(-1).month;
  $('fundCompany').innerHTML='<option value="">Todas as empresas</option>'+[...new Map(d.instruments.map(i=>[i.operation,i.label]))].map(([id,name])=>`<option value="${id}">${U.esc(name)}</option>`).join('');
  $('fundStatus').textContent=`Base de cálculo: ${d.generated_at} · ${d.instruments.filter(i=>i.eligible).length} instrumentos com composição de 1/6 · planejamento sem consulta a contas bancárias.`;
  $('fundContent').hidden=false;render();
}catch(error){$('fundStatus').classList.add('error');$('fundStatus').textContent='Não foi possível carregar a recomposição: '+error.message;}}
for(const id of ['fundMonth','fundCompany','fundFilter'])$(id).addEventListener('change',()=>{if($('fundMonth').value)render();});
$('fundInstrument').addEventListener('change',e=>{state.code=e.target.value;renderDetail();});
$('fundRows').addEventListener('click',e=>{const b=e.target.closest('[data-fund]');if(b){state.code=b.dataset.fund;$('fundInstrument').value=state.code;renderDetail();$('fundDetail').scrollIntoView({behavior:'smooth',block:'start'});}});
for(const id of ['fundChart','fundProjection'])$(id).addEventListener('click',e=>{const b=e.target.closest('[data-month]');if(b){$('fundMonth').value=b.dataset.month;render();}});
$('exportFunds').addEventListener('click',()=>U.download(`recomposicao-${state.month}.csv`,U.csv([['Competência','Empresa','Série','IF','PMT alvo','PMT R$','Aporte R$','Parcela','Natureza','Situação','Base'],...state.visible.map(({i,row,cycle,status})=>[state.month,i.label,i.series,i.code,cycle?.payment_date,cycle?.payment.replace('.',','),(row?.amount||'0.00').replace('.',','),row?`${row.installment}/6`:'',i.rank,status==='active'?'Em composição':status==='waiting'?'Em carência':'Ciclo encerrado',state.data.generated_at])]),'text/csv;charset=utf-8'));
load();
