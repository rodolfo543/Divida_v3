'use strict';
const K = window.CalendarCore;
const el = id => document.getElementById(id);
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const calendarState = {data:null, selected:null, year:0, month:0, operation:'', type:'', today:null, filtered:[], grouped:new Map()};
const counted = (n, single, plural=single+'s') => `${n} ${n===1?single:plural}`;
function todayInBrazil() {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).map(p=>[p.type,p.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}
function dateText(d, options = {day:'numeric',month:'long'}) {return new Intl.DateTimeFormat('pt-BR',{timeZone:'UTC',...options}).format(K.parse(d));}
function shortMoney(n) {
  const number = Number(n)/100;
  return number >= 1e9 ? (number/1e9).toLocaleString('pt-BR',{maximumFractionDigits:2})+' bi' : number >= 1e6 ? (number/1e6).toLocaleString('pt-BR',{maximumFractionDigits:2})+' mi' : number >= 1000 ? (number/1000).toLocaleString('pt-BR',{maximumFractionDigits:1})+' mil' : number.toLocaleString('pt-BR',{maximumFractionDigits:2});
}
function typeName(event) {return event.type==='payment'?'PMT':event.type==='incorporation'?'Incorporação':'Vencimento';}
function currentKey() {return K.monthKey(calendarState.year,calendarState.month);}
function withinMonth() {return calendarState.filtered.filter(e=>e.date.startsWith(currentKey()));}
function chooseDate(date, scroll=false) {
  const year=Number(date.slice(0,4)), options=el('yearSelect').options;
  if(options.length && (year<Number(options[0].value)||year>Number(options[options.length-1].value)))return;
  calendarState.selected=date; const parsed=K.parse(date); calendarState.year=parsed.getUTCFullYear(); calendarState.month=parsed.getUTCMonth();
  render();
  if (scroll && window.matchMedia('(max-width:850px)').matches) el('dayPanel').scrollIntoView({behavior:'smooth',block:'start'});
}
function changeMonth(amount) {
  const date=new Date(Date.UTC(calendarState.year,calendarState.month+amount,1));
  calendarState.year=date.getUTCFullYear(); calendarState.month=date.getUTCMonth();
  if(calendarState.year < Number(el('yearSelect').options[0].value) || calendarState.year > Number(el('yearSelect').options[el('yearSelect').options.length-1].value)) {
    calendarState.year-=amount>0?1:-1; calendarState.month=amount>0?11:0; return;
  }
  selectMonthDay(); render();
}
function selectMonthDay() {
  const events=withinMonth(); calendarState.selected=events.find(e=>e.date>=calendarState.today)?.date || events[0]?.date || currentKey()+'-01';
}
function updateFilter() {
  calendarState.operation=el('companyFilter').value; calendarState.type=el('typeFilter').value;
  calendarState.filtered=calendarState.data.events.filter(e=>K.matches(e,calendarState.operation,calendarState.type));
  calendarState.grouped=K.grouped(calendarState.filtered); render();
}
function render() {
  const s=calendarState, rows=withinMonth(), payments=rows.filter(e=>K.cents(e.payment)>0n), countDays=new Set(rows.map(e=>e.date)).size;
  const next=s.filtered.find(e=>e.date>=s.today);
  el('monthTitle').textContent=`${K.months[s.month]} ${s.year}`; el('yearSelect').value=s.year;
  el('monthGrid').setAttribute('aria-label',`Dias de ${K.months[s.month]} de ${s.year}`);
  const cards=[['PMTs no mês',K.cash(K.sum(rows)),`${counted(payments.length,'pagamento')} · juros e amortização`],
    ['Incorporações no mês',K.cash(K.sum(rows,'incorporation')),'Sem saída de caixa · acrescem ao saldo'],
    ['Dias com compromissos',String(countDays),`${counted(rows.length,'evento')} em ${K.months[s.month].toLocaleLowerCase('pt-BR')}`],
    ['Próximo compromisso',next?dateText(next.date,{day:'2-digit',month:'short'}):'Sem previsão',next?`${dateText(next.date,{year:'numeric'})} · ${counted(s.grouped.get(next.date).length,'evento')} na data`:'Nos cronogramas selecionados']];
  el('calendarMetrics').innerHTML=cards.map(([a,b,c])=>`<article class="calendar-metric"><span>${a}</span><strong>${b}</strong><small>${c}</small></article>`).join('');
  el('monthStrip').innerHTML=K.months.map((name,m)=>`<button type="button" data-month="${m}" class="${s.filtered.some(e=>e.date.startsWith(K.monthKey(s.year,m)))?'has-events':''}" aria-pressed="${m===s.month}" aria-label="${name} de ${s.year}">${name.slice(0,3)}</button>`).join('');
  el('filterScope').textContent=`${counted(new Set(s.filtered.map(e=>e.code)).size,'instrumento')} · ${counted(new Set(s.filtered.map(e=>e.operation)).size,'empresa')} nos filtros`;
  el('monthGrid').innerHTML=K.monthDays(s.year,s.month).map(d=>{
    const events=s.grouped.get(d)||[], total=K.sum(events), types=[...new Set(events.map(e=>e.type))], companies=[...new Set(events.map(e=>e.company))];
    const weekend=[0,6].includes(K.parse(d).getUTCDay());
    const description=`${dateText(d,{weekday:'long',day:'numeric',month:'long',year:'numeric'})}. ${events.length?`${events.length} compromissos. PMT ${K.cash(total)}.`:'Sem compromissos nos filtros.'}`;
    return `<button type="button" class="day-cell ${d.startsWith(currentKey())?'':'outside'} ${weekend?'weekend':''} ${events.length?'has-events':''} ${d===s.today?'today':''}" data-date="${d}" aria-label="${escapeHtml(description)}" aria-pressed="${d===s.selected}" ${d===s.today?'aria-current="date"':''}><span class="day-number">${Number(d.slice(-2))}</span><span class="day-dots" aria-hidden="true">${types.map(t=>`<i class="dot ${t}"></i>`).join('')}</span>${events.length?`<span class="day-count">${events.length} ${events.length===1?'evento':'eventos'}</span><span class="day-amount">${total>0n?'R$ '+shortMoney(total):'Sem caixa'}</span><span class="day-company">${escapeHtml(companies[0])}${companies.length>1?' +'+(companies.length-1):''}</span>`:''}</button>`;
  }).join('');
  el('exportCalendar').disabled=rows.length===0;
  const minYear=Number(el('yearSelect').options[0].value), maxYear=Number(el('yearSelect').options[el('yearSelect').options.length-1].value);
  el('previousMonth').disabled=s.year===minYear && s.month===0; el('nextMonth').disabled=s.year===maxYear && s.month===11;
  renderDay(); renderUpcoming();
}
function renderDay() {
  const s=calendarState;
  if(!s.selected) {
    el('selectedWeekday').textContent='Detalhamento';el('selectedDayTitle').textContent='Escolha um dia';el('selectedDayYear').textContent='';el('closeDay').hidden=true;
    el('dayContent').innerHTML='<div class="day-empty"><strong>Seu dia em detalhe.</strong>Clique em uma data do calendário para ver empresas, séries e valores.</div>';return;
  }
  el('closeDay').hidden=false;
  const date=s.selected, events=s.grouped.get(date)||[], future=date>s.data.local_as_of;
  el('selectedWeekday').textContent=dateText(date,{weekday:'long'}); el('selectedDayTitle').textContent=dateText(date);el('selectedDayYear').textContent=`${date.slice(0,4)} · ${date<s.today?'Data passada':date===s.today?'Hoje':'Próximo'}`;
  if(!events.length) {
    const next=s.filtered.find(e=>e.date>date);
    el('dayContent').innerHTML=`<div class="day-empty"><strong>Dia sem compromissos.</strong>Nenhum evento para esta data nos filtros atuais.${next?`<br><button type="button" class="secondary-button" data-jump="${next.date}">Ver ${dateText(next.date)} →</button>`:''}<small>Altere a empresa ou o tipo para ampliar a consulta.</small></div>`;return;
  }
  const incorporated=K.sum(events,'incorporation');
  el('dayContent').innerHTML=`<div class="day-total"><span>Total de PMT no dia</span><strong>${K.cash(K.sum(events))}</strong><small>${counted(events.length,'compromisso')} · ${counted(new Set(events.map(e=>e.operation)).size,'empresa')}${incorporated>0n?`<br>${K.cash(incorporated)} em incorporações, sem caixa.`:''}</small></div>`+events.map(e=>{
    const cash=K.cents(e.payment)>0n;
    return `<article class="event-card"><div class="event-topline"><strong>${escapeHtml(e.company)}</strong><span class="event-type ${e.type}">${typeName(e)}</span></div><p class="series-line">${escapeHtml(e.series)} · ${escapeHtml(e.code)}</p><p class="event-amount">${K.cash(K.cents(cash?e.payment:e.incorporation))}</p><dl>${cash?`<dt>Juros pagos</dt><dd>${K.cash(K.cents(e.interest))}</dd><dt>Amortização ordinária</dt><dd>${K.cash(K.cents(e.ordinary))}</dd>${K.cents(e.extra)>0n?`<dt>Amortização extraordinária</dt><dd>${K.cash(K.cents(e.extra))}</dd>`:''}`:`<dt>Juros incorporados</dt><dd>${K.cash(K.cents(e.incorporation))}</dd><dt>Pagamento em caixa</dt><dd>${K.cash(0n)}</dd>`}${e.reference_date && e.reference_date!==e.date?`<dt>Data de referência</dt><dd>${dateText(e.reference_date,{day:'2-digit',month:'2-digit',year:'numeric'})}</dd>`:''}</dl><p class="event-timing">${future?'Valor projetado pelo modelo.':'Evento do cronograma publicado.'} A agenda não confirma liquidação.${[0,6].includes(K.parse(date).getUTCDay())?' Data do cronograma em fim de semana; conferir a regra contratual de liquidação.':''}</p>${e.pending?`<p class="event-pending">Pendência de conciliação: ${escapeHtml(e.note)}</p>`:''}<a href="./vortx.html?instrument=${encodeURIComponent(e.code)}">Conferir instrumento na conciliação ↗</a></article>`;
  }).join('');
}
function renderUpcoming() {
  const entries=[...calendarState.grouped.entries()].filter(([d])=>d>=calendarState.today).slice(0,4);
  el('upcomingList').innerHTML=entries.map(([date,events])=>`<button type="button" class="upcoming-day" data-jump="${date}"><span>${dateText(date,{day:'2-digit',month:'short',year:'numeric'})} ↗</span><strong>${K.cash(K.sum(events))}</strong><small>${counted(events.length,'compromisso')} · ${counted(new Set(events.map(e=>e.company)).size,'empresa')}${K.sum(events,'incorporation')>0n?'<br>Também há incorporação sem caixa.':''}</small></button>`).join('')||'<p class="calendar-status">Nenhum compromisso futuro nos filtros selecionados.</p>';
}
async function loadCalendar() {
  try {
    const response=await fetch('./data/calendar.json',{cache:'no-cache'});if(!response.ok)throw new Error(`HTTP ${response.status}`);
    calendarState.data=await response.json(); const s=calendarState;s.today=todayInBrazil();
    const companies=[...new Map(s.data.instruments.map(i=>[i.operation,i.label]))];
    el('companyFilter').innerHTML='<option value="">Todas as empresas</option>'+companies.map(([id,name])=>`<option value="${escapeHtml(id)}">${escapeHtml(name)}</option>`).join('');
    const years=s.data.events.map(e=>Number(e.date.slice(0,4))), nowYear=Number(s.today.slice(0,4));
    const first=Math.min(nowYear,...years), last=Math.max(nowYear,...years);
    el('yearSelect').innerHTML=Array.from({length:last-first+1},(_,i)=>`<option value="${first+i}">${first+i}</option>`).join('');
    el('generationDate').textContent=`Base: ${s.data.generated_at}`;
    el('calendarStatus').textContent=`${s.data.events.length.toLocaleString('pt-BR')} eventos · ${s.data.instruments.length} instrumentos · cronogramas completos de ${first} a ${last}.`;
    el('calendarNote').textContent=`Agenda extraída dos cálculos publicados em ${s.data.generated_at}. Datas preservadas conforme os cronogramas; nenhum evento é remarcado nesta aba. Valores futuros são projeções sujeitas aos índices. Eventos passados não significam pagamentos confirmados. As pendências de AXS 05 e AXS 11 são sinalizadas nos detalhes.`;
    el('calendarContent').hidden=false;
    s.filtered=s.data.events;s.grouped=K.grouped(s.filtered);
    const requested=new URLSearchParams(location.search).get('date');
    const valid=requested && /^\d{4}-\d{2}-\d{2}$/.test(requested) && !Number.isNaN(K.parse(requested).getTime()) && K.iso(K.parse(requested))===requested && Number(requested.slice(0,4))>=first && Number(requested.slice(0,4))<=last;
    chooseDate(valid?requested:s.filtered.find(e=>e.date>=s.today)?.date||s.today);
  } catch(error) {el('calendarStatus').classList.add('error');el('calendarStatus').textContent=`Não foi possível carregar a agenda (${error.message}). Recarregue a página.`;}
}
el('companyFilter').addEventListener('change',updateFilter);el('typeFilter').addEventListener('change',updateFilter);
el('previousMonth').addEventListener('click',()=>changeMonth(-1));el('nextMonth').addEventListener('click',()=>changeMonth(1));
el('todayButton').addEventListener('click',()=>chooseDate(calendarState.today));
el('yearSelect').addEventListener('change',e=>{calendarState.year=Number(e.target.value);selectMonthDay();render();});
el('monthStrip').addEventListener('click',e=>{const b=e.target.closest('[data-month]');if(b){calendarState.month=Number(b.dataset.month);selectMonthDay();render();}});
el('monthGrid').addEventListener('click',e=>{const b=e.target.closest('[data-date]');if(b){const date=b.dataset.date;chooseDate(date,true);document.querySelector(`#monthGrid [data-date="${date}"]`)?.focus({preventScroll:true});}});
el('monthGrid').addEventListener('keydown',e=>{
  const button=e.target.closest('[data-date]');if(!button)return;
  const move={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7}[e.key];if(move===undefined)return;
  const date=K.shift(button.dataset.date,move), year=Number(date.slice(0,4)), options=el('yearSelect').options;
  if(year<Number(options[0].value)||year>Number(options[options.length-1].value))return;
  e.preventDefault();chooseDate(date);document.querySelector(`#monthGrid [data-date="${date}"]`)?.focus();
});
for(const id of ['dayContent','upcomingList'])el(id).addEventListener('click',e=>{const button=e.target.closest('[data-jump]');if(button)chooseDate(button.dataset.jump,true);});
el('closeDay').addEventListener('click',()=>{const selected=calendarState.selected;calendarState.selected=null;render();document.querySelector(`#monthGrid [data-date="${selected}"]`)?.focus();});
el('exportCalendar').addEventListener('click',()=>{
  const content=K.calendarFile(withinMonth(),calendarState.data.built_at), url=URL.createObjectURL(new Blob([content],{type:'text/calendar;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=`agenda-axs-${currentKey()}.ics`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
loadCalendar();
