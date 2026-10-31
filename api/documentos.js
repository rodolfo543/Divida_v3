const catalog=require('../vortx_catalog.json');
const snapshot=require('../data/documents.json');
const {normalize,allowedUrl}=require('../documents-core.js');
const cache=new Map(),BASE='https://apis.vortx.com.br/vxsite/api/operacao';
async function collect(config,fetcher=fetch){
  const documents=new Map(),errors=[],now=new Date().toISOString();
  await Promise.all([0,1].map(async route=>{try{
    const response=await fetcher(`${BASE}/${config.operation_id}/documentos-por-tipo/${route}`,{headers:{Accept:'application/json','User-Agent':'AXS-Debt-Documents/1.0'},signal:AbortSignal.timeout(18000)});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    for(const d of normalize(await response.json(),config.code,true))documents.set(d.id,d);
  }catch(e){errors.push(`Consulta ${route}: ${e.message}`);}}));
  return {code:config.code,documents:[...documents.values()],errors,collected_at:errors.length?null:now,attempted_at:now};
}
module.exports=async function handler(req,res){
  res.setHeader('Cache-Control','private, no-store');
  if(req.method!=='GET'){res.setHeader('Allow','GET');return res.status(405).json({error:'Use GET'});}
  const config=catalog.find(i=>i.code===req.query?.instrument);
  if(!config)return res.status(400).json({error:'Instrumento não cadastrado'});
  const requested=req.query?.document;
  if(requested!==undefined&&!/^\d+$/.test(requested))return res.status(400).json({error:'Documento inválido'});
  let entry=cache.get(config.code);
  const expires=d=>{try{const e=new URL(d.url).searchParams.get('Expires');return e?Number(e)*1000:Infinity;}catch{return 0;}};
  if(!entry||Date.now()-entry.time>300000||requested&&entry.value.documents.some(d=>d.id===requested&&expires(d)<Date.now()+30000)){
    entry={time:Date.now(),value:await collect(config)};cache.set(config.code,entry);
  }
  const live=entry.value,old=snapshot.instruments.find(i=>i.code===config.code);
  if(requested){
    const doc=live.documents.find(d=>d.id===requested);
    if(doc&&allowedUrl(doc.url)){res.setHeader('Location',doc.url);return res.status(302).end();}
    const exists=old?.documents.some(d=>d.id===requested);
    if(exists&&live.errors.length){res.setHeader('Location',`https://www.vortx.com.br/investidor/dcm/operacao?id=${config.operation_id}&page=3`);return res.status(302).end();}
    return res.status(404).json({error:'Documento público não disponível nesta operação.'});
  }
  const documents=new Map(live.documents.map(({url,...d})=>[d.id,d]));
  if(live.errors.length)for(const d of old?.documents||[])if(!documents.has(d.id))documents.set(d.id,d);
  return res.status(200).json({...live,documents:[...documents.values()],collected_at:live.errors.length?old?.collected_at||null:live.collected_at,cached:live.errors.length>0});
};
module.exports.collect=collect;
