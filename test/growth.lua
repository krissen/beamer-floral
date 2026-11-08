-- Adapter contract tests, independent of the expensive botanical painter.
-- Run: texlua test/growth.lua /path/to/tikz-flora
package.path=arg[1]..'/lua/?.lua;'..package.path
local emitted={}
tex={error=function(s) error(s) end,sprint=function(s) emitted[#emitted+1]=s end}
local planned,rendered=0,{}
package.loaded['flora.progression']={api_version=1,
  plan=function(spec) planned=planned+1; return {spec=spec} end,
  stages=function(plan,n)
    local levels={};for k=1,n do levels[k]=k/n end;return levels
  end,
  render=function(plan,t) rendered[#rendered+1]=t;return {plan=plan,t=t} end}
flora={settings={},reserve={},render_page_version=1,seed=function(base,id) return id end,
  typeset_page=function(pt,spec,a) assert(pt and spec.width==400 and a.test) end}
local M=dofile('beamer-floral.lua')
local function spec()
  return {width=400,height=300,text={x0=30,y0=20,x1=370,y1=270},
    lines={},doc_seed='3',reserve={}}
end
local path=os.tmpname(); os.remove(path)
-- Establish a prior run with four displayed overlays.
flora.settings={growth='overlays'}
M.init(path);M.context(1,0,true,false)
for i=1,4 do M.prepare(spec()) end
M.finish()
M.init(path);M.context(1,0,true,false)
for i=1,4 do
  local s=spec(); M.prepare(s)
  local pt=M.render_page(s,{test=true})
  assert(pt.t==i/4)
end
assert(planned==1,'one plan must serve all stable overlays')
assert(rendered[4]==1,'final overlay must be complete')
-- Timed uses the same intervals and preserves endpoints after rounding.
M.frame.growth={growth='timed',['growth duration']=8,['growth fps']=20}
M.animation_support=true
local stable=spec();stable.seed=1;stable.page=1
for i=1,4 do
  M.stage=i
  assert(M.render_page(stable,{test=true})==true)
  assert(M.animation.steps==40)
  local start=#rendered
  M.paint_animation(0); M.paint_animation(M.animation.steps)
  assert(rendered[start+1]==(i-1)/4 and rendered[start+2]==i/4)
end
assert(planned==1,'animation must reuse the overlay plan')
-- A raster interval must not switch back to vectors at either boundary.
kpse={find_file=function(name)return name end}
package.loaded['flora.paint']={new=function()
  return {emit=function(_,s)emitted[#emitted+1]=s end}
end}
M.animation.raster={prefix='cache/sample-',stage=2}
M.animation.steps=2
local before=#rendered
M.paint_animation(0);M.paint_animation(2)
assert(#rendered==before,'raster endpoints must stay on the cached image path')
assert(emitted[#emitted-1]:find('sample-2.png',1,true),'interval start uses the shared boundary image')
assert(emitted[#emitted]:find('sample-4.png',1,true),'interval end uses the final cached image')
M.frame.growth['growth duration']=0.01
M.render_page(stable,{test=true});assert(M.animation.steps==1,'short interval still needs both endpoints')
M.animation_support=false
assert(not pcall(M.render_page,spec(),{test=true}),'timed needs explicit package support')
M.handout=true
assert(M.render_page(spec(),{})==nil,'handout delegates complete static painting')
M.handout=false;M.frame.growth.growth='off'
assert(M.render_page(spec(),{})==nil,'off delegates ordinary painting')
os.remove(path)
print('growth adapter contract tests passed')
