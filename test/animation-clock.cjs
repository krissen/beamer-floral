// Exercise the actual JavaScript extracted from the generated PDF.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync(process.argv[2], 'utf8');
const closing = fs.readFileSync(process.argv[3], 'utf8');
const invisible = fs.readFileSync(process.argv[4], 'utf8');
const startup = fs.readFileSync(process.argv[5], 'utf8');
const id = code.match(/var a(\d+)_floralEpoch/)[1];
const last = Number(code.match(/if\(target>=(\d+)\)/)[1]);
const fps = Number(code.match(new RegExp(`a${id}_fps=([0-9.e+-]+);`))[1]);
const label = code.match(/anim\['([^']+)'\]/)[1];
let now = 10000;
const layers = Array.from({length:last+1}, (_,i) => ({
  name:`${id}.${i}`,initState:i===last,state:i===last
}));
const siblingId = [...startup.matchAll(/"(\d+)":true/g)].map(x=>x[1]).find(x=>x!==id);
const sibling = siblingId && [{name:`${siblingId}.0`,state:false},
  {name:`${siblingId}.1`,state:true}];
if(sibling) layers.push(...sibling);
const context = {Date:class extends Date {constructor(){super(now)}},
  getOCGs:()=>layers,pageNum:0,
  app:{setInterval:()=>1,clearInterval:()=>{}},console};
vm.createContext(context);
vm.runInContext(startup,context);
assert.equal(layers[0].state,true,'unvisited page must already show the start before PageOpen');
assert.equal(layers[last].state,false,'endpoint must not flash before PageOpen');
vm.runInContext(code,context);
const animation = context.anim[label];
assert.equal(animation.frameNum,0);
now = 10000 + Math.floor(last * 500 / fps);
vm.runInContext(`a${id}_gotoNext()`,context);
assert.equal(animation.frameNum,Math.max(1,Math.floor(Math.floor(last*500/fps)*fps/1000)), 'late timers must catch up');
now = 10000 + Math.ceil(last * 1000 / fps);
vm.runInContext(`a${id}_gotoNext()`,context);
assert.equal(animation.frameNum,last);
assert.equal(animation.isPlaying,false,'must stop at endpoint');
now += 60000;
vm.runInContext(code,context);
assert.equal(animation.frameNum,last,'duplicate page-visible events must not replay');
assert.equal(animation.isPlaying,false,'a finished interval must stay stopped');
if(sibling){sibling[0].state=false;sibling[1].state=true;}
vm.runInContext(closing,context);
assert.equal(animation.frameNum,last,'PageClose must not redraw a still-visible outgoing page');
if(sibling){
  assert.equal(sibling[0].state,true,'other pages must be prepared before their next entry');
  assert.equal(sibling[1].state,false,'other pages must not retain a finished layer');
}
vm.runInContext(invisible,context);
assert.equal(animation.frameNum,0,'rearm only after PageInvisible');
vm.runInContext(code,context);
assert.equal(animation.frameNum,0,'page reentry must restart');
assert.equal(animation.isPlaying,true);
assert.equal(layers.filter(x=>x.name.startsWith(id+'.')&&x.state).length,1,'only one OCG per animation should be visible');
console.log(`PDF clock ${label}: catch-up, endpoint and replay passed`);
