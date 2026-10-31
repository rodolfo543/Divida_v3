'use strict';
window.FinanceUI = {
  esc: value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
  day: d => d ? d.slice(0,10).split('-').reverse().join('/') : '—',
  month: m => m ? new Intl.DateTimeFormat('pt-BR',{month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(m+'-01T12:00:00Z')) : '—',
  async json(url) {const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();},
  download(name,content,type) {const url=URL.createObjectURL(new Blob([content],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);},
  csv(rows) {return '\ufeff'+rows.map(r=>r.map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(';')).join('\r\n');}
};
