-- Run: texlua test/overlays.lua /path/to/tikz-flora
package.path=arg[1]..'/lua/?.lua;'..package.path
local written={}
tex={error=function(s) error(s) end,sprint=function(s) written[#written+1]=s end}
flora={settings={layout='surround'},reserve={},seed=function(base,id) return tonumber(base)*7919+id*104729 end}
local M=dofile('beamer-floral.lua')
local function spec(x)
  return {width=400,height=300,text={x0=30,y0=20,x1=370,y1=270},
    lines={{x0=x,y0=80,x1=x+50,y1=95}},header_y=280,frametitle=false,
    doc_seed='3',reserve={},layout='surround',mix={density=1}}
end
local path=os.tmpname();os.remove(path)
M.init(path)
M.context(1,0,true)
local first=spec(50);M.prepare(first)
local second=spec(150);M.prepare(second)
assert(first.seed==second.seed)
assert(#M.current[1].geometry.lines==2)
M.finish();assert(#written==1)
M.init(path);written={}
M.context(1,0,true)
first=spec(50);M.prepare(first)
second=spec(150);M.prepare(second)
assert(#first.lines==2 and #second.lines==2)
assert(require('flora.serial').encode(first)==require('flora.serial').encode(second))
local transient=spec(150);transient.palette={blooms='blue'};M.prepare(transient)
assert(transient.palette==nil,'nil snapshot fields must be restored')
M.finish();assert(#written==0,'cache must converge')
M.context(3,0,true);local nextframe=spec(50);M.prepare(nextframe)
assert(nextframe.seed~=first.seed,'unnumbered invocation must get separate seed')
M.context(3,1,true);assert(M.count==3,'continuations have separate identities')
M.context(4,0,true);M.prepare(spec(50));flora.settings.layout='left'
assert(not pcall(M.prepare,spec(60)),'midframe document settings must fail')
flora.settings.layout='surround'
M.context(5,0,true);M.input_signature='orange';M.prepare(spec(50))
M.input_signature='blue'
assert(not pcall(M.prepare,spec(50)),'background changes within a frame must fail')
assert(not pcall(M._decode,'os.execute("bad")'),'cache cannot execute code')
assert(not pcall(M._decode,'beamer-floral-cache-1\nS\t1\t61\nG\t1\ttext\t50\t0\t10\t20\n'),
  'cache rectangles must have ordered coordinates')
local f=assert(io.open(path,'w'));f:write('broken cache');f:close()
M.init(path);assert(next(M.previous)==nil,'corrupt cache must rebuild')
os.remove(path)
M.init(path);assert(M.old==nil,'missing cache must not retain a previous initialization')
M.context(1,0,true,false);local untitled=spec(50);untitled.header='body';M.prepare(untitled)
assert(untitled.body_top==270 and not untitled.frametitle,'untitled frames must respect headline without inventing a title')
M.context(2,0,true,true);local plain=spec(50);plain.header='body';M.prepare(plain)
assert(plain.body_top==nil,'plain frames must retain the unrestricted canvas')
print('overlay unit tests passed')
