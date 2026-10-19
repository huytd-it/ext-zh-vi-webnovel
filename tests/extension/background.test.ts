import {beforeEach, describe, expect, it, vi} from 'vitest';

const extensionId = 'a'.repeat(32);
const ownUrl = `chrome-extension://${extensionId}/ui/options.html`;
const uiSender = {id:extensionId, url:ownUrl, tab:{id:100}};
const pageSender = (tab=7) => ({id:extensionId, url:'https://novel.test/chapter', tab:{id:tab}});
let listener: (m:any, s:any, reply:(r:any)=>void)=>boolean;
let session: Record<string,any>, local: Record<string,any>;
let fetchMock: ReturnType<typeof vi.fn>;
let jobNumber: number;

const send = (body: unknown, sender=uiSender) => new Promise<any>(resolve => listener(body,sender,resolve));
async function install() {
  vi.resetModules();
  await import('../../extension/src/background/index');
}
beforeEach(async () => {
  session = {}; local = {token:'secret-test-token-not-for-page'}; jobNumber=0;
  const storage = (values:Record<string,any>) => ({
    get: vi.fn(async (key:string) => ({[key]:structuredClone(values[key])})),
    set: vi.fn(async (data:any) => Object.assign(values,structuredClone(data))),
    remove: vi.fn(async (key:string) => {delete values[key];}),
    setAccessLevel: vi.fn(async () => {})
  });
  vi.stubGlobal('chrome', {
    runtime:{id:extensionId, getURL:(p:string)=>`chrome-extension://${extensionId}/${p}`,
      onMessage:{addListener:(f:typeof listener)=>{listener=f;}}},
    storage:{local:storage(local),session:storage(session)},
    tabs:{get:vi.fn(async id=>({id,url:'https://novel.test/chapter'})),
      sendMessage:vi.fn(async ()=>({state:'Đang dịch'})),onRemoved:{addListener:vi.fn()}},
    scripting:{executeScript:vi.fn(async ()=>{})}
  });
  fetchMock = vi.fn(async (url:string, options:RequestInit) => {
    const route=url.replace('http://127.0.0.1:17865/v1','');
    let data:any = {};
    if (route==='/models') data=[{id:'HachimiMT-60',ready:true,blocked:false}];
    if (route==='/glossaries') data=[{id:'novel',name:'Truyện',entries:[{source:'张三',target:'Trương Tam',enabled:true}]}];
    if (route==='/jobs' && options.method==='POST') data={id:`job-${++jobNumber}`,version:JSON.parse(options.body as string).version,state:'queued',results:[]};
    if (route.startsWith('/jobs/') && options.method==='GET') data={id:route.split('/')[2],state:'complete',results:[]};
    return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});
  });
  vi.stubGlobal('fetch',fetchMock);
  await install();
});

describe('MV3 background boundary and recovery', () => {
  it('accepts its settings page even when Chrome supplies sender.tab', async () => {
    expect((await send({type:'health'})).ok).toBe(true);
    expect(chrome.storage.local.setAccessLevel).toHaveBeenCalledWith({accessLevel:'TRUSTED_CONTEXTS'});
  });
  it('rejects foreign extension senders and content administrative requests', async () => {
    expect((await send({type:'health'}, {...uiSender,id:'foreign'})).ok).toBe(false);
    expect((await send({type:'health'},pageSender())).ok).toBe(false);
    expect((await send({type:'download',id:'HachimiMT-60'},pageSender())).ok).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it('preserves immutable glossary snapshot and recovers job ID after worker reload', async () => {
    const started = await send({type:'start',tab:7,config:{model:'HachimiMT-60',device:'cpu',glossary_id:'novel'}});
    expect(started.ok).toBe(true);
    const version = started.data.version;
    const batch = await send({type:'batch',version,units:[{id:'1',text:'张三'}]},pageSender());
    expect(batch.ok).toBe(true);
    const request = fetchMock.mock.calls.find(([url,options])=>url.endsWith('/jobs') && options.method==='POST')!;
    const body=JSON.parse(request[1].body as string);
    expect(body.glossary_entries[0].target).toBe('Trương Tam');
    expect(body.glossary_id).toBeNull();
    await install();
    const poll=await send({type:'poll',version},pageSender());
    expect(poll.ok).toBe(true);
    expect(fetchMock.mock.calls.at(-1)![0]).toMatch(/\/jobs\/job-1$/);
    expect(session['tab-7'].job).toBeUndefined();
    expect((await send({type:'poll',version:'stale'},pageSender())).ok).toBe(false);
  });
  it('keeps separate tab sessions and removes the stopped session', async () => {
    const config={model:'HachimiMT-60',device:'cpu',glossary_id:null};
    const a=await send({type:'start',tab:7,config});
    const b=await send({type:'start',tab:8,config});
    expect(a.data.version).not.toBe(b.data.version);
    expect((await send({type:'batch',version:a.data.version,units:[{id:'1',text:'中'}]},pageSender(8))).ok).toBe(false);
    await send({type:'control',tab:7,action:'stop'});
    expect(session['tab-7']).toBeUndefined();
    expect(session['tab-8'].version).toBe(b.data.version);
  });
  it('never accepts a model ID as an arbitrary URL', async () => {
    expect((await send({type:'download-info',id:'https://attacker.test'})).ok).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
