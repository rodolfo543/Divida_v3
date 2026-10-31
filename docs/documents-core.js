(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.DocumentsCore=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  function allowedUrl(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&(!u.port||u.port==='443')&&u.hostname.endsWith('.vortx.com.br');}catch{return false;}}
  function normalize(groups,code,withUrl=false){
    if(!Array.isArray(groups))throw new Error('Resposta de documentos inválida');
    const docs=new Map();
    for(const group of groups)for(const d of group.documents||[]){
      if(d.public!==true||!allowedUrl(d.url)||!/^\d+$/.test(String(d.id)))continue;
      docs.set(String(d.id),{id:String(d.id),name:d.description||`Documento ${d.id}`,category:d.type||group.type||'Outros documentos',type_id:d.typeId??null,uploaded_at:d.uploadTimestamp??null,source_operation_id:d.operationId??null,code,...(withUrl?{url:d.url}:{})});
    }
    return [...docs.values()];
  }
  function unique(instruments){const map=new Map();for(const i of instruments)for(const d of i.documents){const old=map.get(d.id);if(old){if(!old.codes.includes(i.code))old.codes.push(i.code);}else map.set(d.id,{...d,codes:[i.code],operation:i.operation,label:i.label});}return [...map.values()];}
  function search(text,query){const clean=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();return clean(text).includes(clean(query));}
  function categoryTitle(value){return {'Emissao Debentures':'Escrituras e aditivos','Cessao Fiduciaria':'Cessão fiduciária','AF Acoes':'AF de ações','AF de Máquinas':'AF de equipamentos','AF de Outros':'Outras garantias','Mat':'Matrículas','DFP':'Demonstrações financeiras','ARCA/AGE':'Atas societárias','Relatório Garantias':'Relatórios de garantias'}[value]||value;}
  return {allowedUrl,normalize,unique,search,categoryTitle};
});
