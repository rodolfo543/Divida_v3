const assert=require('node:assert/strict');
const D=require('./documents-core.js');
const handler=require('./api/documentos.js');
async function run(){
  assert.ok(D.allowedUrl('https://arquivos-vx-informa.vortx.com.br/test.pdf?Expires=9999999999'));
  for(const url of ['http://assets-web.vortx.com.br/a.pdf','https://vortx.com.br.evil.com/a.pdf','https://user:pass@assets-web.vortx.com.br/a.pdf','javascript:alert(1)','file:///etc/passwd'])assert.equal(D.allowedUrl(url),false,url);
  const source=[{type:'Escritura',documents:[{id:123,public:true,description:'Contrato.pdf',url:'https://assets-web.vortx.com.br/a.pdf',userId:1},{id:124,public:false,url:'https://assets-web.vortx.com.br/private.pdf'}]}];
  const normalized=D.normalize(source,'PAXS12');assert.equal(normalized.length,1);assert.equal(normalized[0].url,undefined);assert.equal(normalized[0].userId,undefined);
  const docs=D.unique([{code:'AXSA11',operation:'axs01',label:'AXS 01',documents:normalized},{code:'AXSA21',operation:'axs01',label:'AXS 01',documents:normalized}]);
  assert.equal(docs.length,1);assert.deepEqual(docs[0].codes,['AXSA11','AXSA21']);assert.equal(D.search('Cessão Fiduciária','cessao'),true);
  const live=await handler.collect({code:'PAXS12',operation_id:97938},async()=>({ok:true,json:async()=>source}));assert.equal(live.documents.length,1);assert.ok(live.documents[0].url);assert.equal(live.errors.length,0);
  const failure=await handler.collect({code:'PAXS12',operation_id:97938},async()=>{throw new Error('offline');});assert.equal(failure.errors.length,2);assert.equal(failure.collected_at,null);
  const response=()=>({setHeader(){},status(n){this.code=n;return this;},json(d){this.body=d;return this;}});
  let r=response();await handler({method:'POST',query:{}},r);assert.equal(r.code,405);
  r=response();await handler({method:'GET',query:{instrument:'https://example.com'}},r);assert.equal(r.code,400);
  r=response();await handler({method:'GET',query:{instrument:'PAXS12',document:'../secrets'}},r);assert.equal(r.code,400);
  console.log('Documentação: arquivos públicos, URLs permitidas, deduplicação, cache e validação da API verificados.');
}
run().catch(e=>{console.error(e);process.exitCode=1;});
