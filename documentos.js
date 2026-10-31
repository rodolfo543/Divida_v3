'use strict';
const U=window.FinanceUI,D=window.DocumentsCore,$=id=>document.getElementById(id);
const s={data:null,company:'',code:'',category:'',visible:[]};
const counted=(n,one,plural=one+'s')=>`${n} ${n===1?one:plural}`;
const folder='<span class="folder-icon" aria-hidden="true"><svg viewBox="0 0 32 25" fill="none"><path d="M2 7V4a2 2 0 012-2h8l3 4h13a2 2 0 012 2v13a2 2 0 01-2 2H4a2 2 0 01-2-2V7Z" fill="currentColor" fill-opacity=".16" stroke="currentColor" stroke-width="1.5"/><path d="M3 8h27" stroke="currentColor" stroke-width="1.5"/></svg></span>';
function instruments(){return s.data.instruments.filter(i=>(!s.company||i.operation===s.company)&&(!s.code||i.code===s.code));}
function categories(items){return [...new Set(D.unique(items).map(d=>d.category))].sort((a,b)=>a.localeCompare(b,'pt-BR'));}
function go(company='',code='',category=''){s.company=company;s.code=code;s.category=category;$('documentSearch').value='';$('documentType').value='';$('documentYear').value='';render();}
function fileLink(d){return `./api/documentos?instrument=${encodeURIComponent(d.code)}&document=${encodeURIComponent(d.id)}`;}
function render(){
  const all=s.data.instruments,companies=[...new Map(all.map(i=>[i.operation,i.label]))],allDocs=D.unique(all),scoped=instruments(),base=D.unique(scoped);
  const current=all.find(i=>i.code===s.code),name=companies.find(([id])=>id===s.company)?.[1];
  const query=$('documentSearch').value,type=$('documentType').value,year=$('documentYear').value;
  const filtered=base.filter(d=>(!s.category||d.category===s.category)&&(!type||d.category===type)&&(!year||(d.uploaded_at||'').startsWith(year))&&D.search(`${d.name} ${d.category} ${D.categoryTitle(d.category)} ${d.codes.join(' ')} ${d.label}`,query));s.visible=filtered;
  const last=all.map(i=>i.collected_at).filter(Boolean).sort().at(-1);
  $('documentMetrics').innerHTML=[['Empresas',companies.length,'Estrutura por empresa'],['Operações / instrumentos',all.length,'Emissões e séries identificadas'],['Documentos públicos',allDocs.length,'Arquivos únicos no catálogo'],['Última coleta válida',last?new Date(last).toLocaleDateString('pt-BR',{timeZone:'America/Sao_Paulo'}):'—','Horário e erros disponíveis na pasta da operação']].map(([a,b,c])=>`<article class="finance-metric"><span>${a}</span><strong>${b}</strong><small>${c}</small></article>`).join('');
  $('folderTree').innerHTML=`<button type="button" data-root class="${!s.company?'active':''}">${folder}Todas as empresas<small>${allDocs.length}</small></button>`+companies.map(([id,label])=>{
    const children=all.filter(i=>i.operation===id),count=D.unique(children).length;
    return `<button type="button" class="tree-company ${s.company===id&&!s.code?'active':''}" data-company="${id}" aria-expanded="${s.company===id}">${folder}${U.esc(label)}<small>${count}</small></button>`+(s.company===id?children.map(i=>`<button type="button" class="tree-operation ${s.code===i.code&&!s.category?'active':''}" data-code="${i.code}">${folder}${U.esc(i.series)}<small>${i.code}</small></button>`+(s.code===i.code?categories([i]).map(c=>`<button type="button" class="tree-category ${s.category===c?'active':''}" data-category="${U.esc(c)}">${folder}${U.esc(c)}</button>`).join(''):'')).join(''):'');
  }).join('');
  $('folderBreadcrumb').innerHTML=`<button type="button" data-root>Empresas</button>${name?`<span>›</span><button type="button" data-company="${s.company}">${U.esc(name)}</button>`:''}${current?`<span>›</span><button type="button" data-code="${current.code}">${U.esc(current.title)}</button>`:''}${s.category?`<span>›</span><span>${U.esc(s.category)}</span>`:''}`;
  $('folderTitle').textContent=D.categoryTitle(s.category)||current?.title||name||'Empresas';
  $('folderDescription').textContent=`${counted(filtered.length,'documento')}${query||type||year?' nos filtros':' nesta pasta e subpastas'}.`;
  const terms=categories(scoped),typeValue=$('documentType').value;
  $('documentType').innerHTML='<option value="">Todos os tipos</option>'+terms.map(c=>`<option value="${U.esc(c)}">${U.esc(D.categoryTitle(c))}</option>`).join('');$('documentType').value=terms.includes(typeValue)?typeValue:'';
  const years=[...new Set(base.map(d=>(d.uploaded_at||'').slice(0,4)).filter(Boolean))].sort().reverse(),yearValue=$('documentYear').value;
  $('documentYear').innerHTML='<option value="">Todos os anos</option>'+years.map(y=>`<option value="${y}">${y}</option>`).join('');$('documentYear').value=years.includes(yearValue)?yearValue:'';
  $('folderActions').innerHTML=current?`<a class="finance-link-button" href="https://www.vortx.com.br/investidor/dcm/operacao?id=${current.operation_id}&page=3" target="_blank" rel="noopener">Pasta na Vórtx ↗</a><a class="finance-link-button" href="https://apis.vortx.com.br/vxsite/api/operacao/${current.code}/memoria-de-calculo" target="_blank" rel="noopener">Memória de cálculo XLSX ↓</a><span class="document-caption">Coleta válida: ${current.collected_at?new Date(current.collected_at).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'}):'não disponível'}${current.errors?.length?' · Coleta parcial; retrato anterior preservado.':''}</span>`:'';
  const searching=!!(query||type||year),cards=[];
  if(!searching&&!s.category){
    if(!s.company)for(const [id,label]of companies){const v=all.filter(i=>i.operation===id);cards.push({attrs:`data-company="${id}"`,title:label,subtitle:`${counted(v.length,'instrumento')} · ${counted(D.unique(v).length,'documento')}`});}
    else if(!s.code)for(const i of scoped)cards.push({attrs:`data-code="${i.code}"`,title:i.title,subtitle:`${i.code} · ${counted(i.documents.length,'documento')}`,empty:!i.documents.length});
    else for(const category of terms)cards.push({attrs:`data-category="${U.esc(category)}"`,title:D.categoryTitle(category),subtitle:counted(base.filter(d=>d.category===category).length,'documento')});
  }
  $('folderGrid').innerHTML=cards.map(c=>`<button type="button" class="folder-card" ${c.attrs}>${folder}<strong>${U.esc(c.title)}</strong><small>${U.esc(c.subtitle)}</small>${c.empty?'<span class="finance-tag">Sem arquivos públicos retornados</span>':''}</button>`).join('');
  const showFiles=searching||s.category,listed=showFiles?filtered:[...filtered].sort((a,b)=>(b.uploaded_at||'').localeCompare(a.uploaded_at||'')).slice(0,8);
  $('fileArea').innerHTML=listed.length?`<h3 class="file-section-heading">${showFiles?'Arquivos da pasta':'Arquivos recentes nesta pasta e subpastas'} · ${listed.length}</h3><div class="finance-scroll"><table class="finance-table file-table"><thead><tr><th>Documento</th><th>Publicado na Vórtx</th><th></th></tr></thead><tbody>${listed.map(d=>`<tr><td><button type="button" class="file-name" data-file="${d.id}"><span class="file-type-icon">${U.esc(d.name.split('.').at(-1).toUpperCase().slice(0,5))}</span><span>${U.esc(d.name)}<small>${U.esc(d.label)} · ${U.esc(d.category)} · ${U.esc(d.codes.join(' / '))}</small></span></button></td><td class="file-upload">${U.day(d.uploaded_at)}</td><td><a class="finance-link-button" href="${fileLink(d)}" target="_blank" rel="noopener" aria-label="Abrir ${U.esc(d.name)}">Abrir ↗</a></td></tr>`).join('')}</tbody></table></div>`:'';
  $('documentEmpty').hidden=cards.length>0||listed.length>0;
  $('documentEmpty').innerHTML=`<strong>${searching?'Nenhum arquivo corresponde aos filtros.':'Nenhum documento público retornado para esta pasta.'}</strong>${searching?'Altere a busca, o tipo ou o ano.':'A ausência de arquivos nesta consulta não significa que a operação não possua documentos. Use o link da Vórtx para consultar a fonte.'}`;
}
function openFile(id){const d=D.unique(instruments()).find(d=>d.id===id);if(!d)return;
  $('fileTitle').textContent=d.name;$('fileDefinition').innerHTML=`<dt>Empresa</dt><dd>${U.esc(d.label)}</dd><dt>Instrumentos</dt><dd>${U.esc(d.codes.join(' / '))}</dd><dt>Tipo na fonte</dt><dd>${U.esc(d.category)}</dd><dt>Publicação</dt><dd>${U.day(d.uploaded_at)}</dd><dt>ID na Vórtx</dt><dd>${d.id}</dd>`;
  $('fileLinks').innerHTML=`<a class="finance-link-button" href="${fileLink(d)}" target="_blank" rel="noopener">Abrir / baixar documento ↗</a>`;$('fileDetails').showModal();}
async function refresh(){
  $('refreshDocuments').disabled=true;let cursor=0,done=0,errors=0;const all=s.data.instruments;
  const work=async()=>{while(cursor<all.length){const i=all[cursor++];try{const result=await U.json(`./api/documentos?instrument=${encodeURIComponent(i.code)}`);if(!Array.isArray(result.documents))throw new Error('Catálogo inválido');Object.assign(i,result);if(result.errors.length)errors++;}catch(error){i.errors=[error.message];errors++;}done++;$('documentStatus').textContent=`Atualizando catálogo: ${done} de ${all.length} instrumentos…`;}};
  await Promise.all([work(),work()]);render();$('refreshDocuments').disabled=false;$('documentStatus').classList.toggle('error',errors>0);$('documentStatus').textContent=errors?`Catálogo atualizado com ${errors} coleta(s) parcial(is). Os retratos anteriores foram preservados.`:'Catálogo público atualizado para os 17 instrumentos. Links de documentos são renovados ao abrir.';
}
async function load(){try{s.data=await U.json('./data/documents.json');const requested=new URLSearchParams(location.search).get('operation');if(s.data.instruments.some(i=>i.operation===requested))s.company=requested;$('documentContent').hidden=false;$('refreshDocuments').disabled=false;render();const errors=s.data.instruments.filter(i=>i.errors.length).length;$('documentStatus').textContent=`Biblioteca de documentos públicos da Vórtx · ${errors?errors+' consulta(s) parcial(is) · ':''}organização por empresa, operação e tipo.`;}catch(error){$('documentStatus').classList.add('error');$('documentStatus').textContent='Não foi possível carregar a biblioteca: '+error.message;}}
for(const id of ['folderTree','folderBreadcrumb','folderGrid'])$(id).addEventListener('click',e=>{const b=e.target.closest('[data-root],[data-company],[data-code],[data-category]');if(!b)return;if(b.hasAttribute('data-root'))go();else if(b.dataset.company)go(b.dataset.company);else if(b.dataset.code){const i=s.data.instruments.find(i=>i.code===b.dataset.code);go(i.operation,i.code);}else if(b.dataset.category)go(s.company,s.code,b.dataset.category);});
$('fileArea').addEventListener('click',e=>{const b=e.target.closest('[data-file]');if(b)openFile(b.dataset.file);});
$('documentSearch').addEventListener('input',render);$('documentType').addEventListener('change',render);$('documentYear').addEventListener('change',render);
$('refreshDocuments').addEventListener('click',refresh);$('closeFile').addEventListener('click',()=>$('fileDetails').close());
$('exportDocuments').addEventListener('click',()=>{const safe=value=>/^[=+@-]/.test(String(value))?"'"+value:value;U.download('documentos-vortx.csv',U.csv([['Empresa','IFs','Tipo','Documento','Publicação','ID'],...s.visible.map(d=>[d.label,d.codes.join(' / '),d.category,safe(d.name),d.uploaded_at,d.id])]),'text/csv;charset=utf-8');});
load();
