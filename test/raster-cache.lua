-- Missing/stale cache must never masquerade as current playback.
-- texlua test/raster-cache.lua /path/to/tikz-flora
package.path=arg[1]..'/lua/?.lua;'..package.path
kpse={find_file=function() return arg[1]..'/tikzflora.sty' end}
local lfs=require('lfs')
local Serial=require('flora.serial')
local engine_cache=arg[1]..'/lua/flora/cache.lua'
package.loaded['flora.cache']=assert(loadfile(engine_cache))('flora.cache',engine_cache)
local C=dofile('beamer-floral-cache.lua')
local root=os.tmpname();os.remove(root);assert(lfs.mkdir(root))
local a={animation_root=root,animation_manifest={},count=1,stage=1,stages=2,
  frame={levels={.5,1}}}
local spec={width=400,height=300,seed=1,text={x0=60,y0=30,x1=350,y1=260}}
assert(C.collect(a,spec,2)==nil,'missing index must be rejected')
local signature=a.animation_manifest[1].signature
assert(#signature==32)
local folder=root..'/'..signature..'-144';assert(lfs.mkdir(folder))
local function write(path,data) local f=assert(io.open(path,'wb'));f:write(data);f:close() end
write(root..'/index.floral',Serial.encode{version=1,frames={[1]={signature=signature,stages=2,steps=2,dpi=144}}})
local png='\137PNG\r\n\26\n'..string.rep('\0',64)
write(folder..'/sample-1.png',png);write(folder..'/sample-3.png',png)
a.animation_cache=nil
assert(C.collect(a,spec,2)==nil,'old interior-only caches need their endpoint samples')
for _,i in ipairs{0,2,4} do write(folder..'/sample-'..i..'.png',png) end
assert(C.collect(a,spec,2).stage==1,'current cache must be usable')
-- Exercise the adapter itself with every expensive progression operation forbidden.
local function forbidden() error('raster path must not plan, validate or render in LaTeX') end
package.loaded['flora.progression']={api_version=1,plan=forbidden,stages=forbidden,render=forbidden}
local oldkpse=kpse
kpse={find_file=function(name) return name end}
tex={error=function(message) error(message) end,sprint=function() end}
flora={render_page_version=1,typeset_page=function() end}
local M=dofile('beamer-floral.lua')
M.frame={growth={growth='timed',['growth duration']=1,['growth fps']=4}}
M.stage=1;M.stages=2;M.count=1;M.animation_root=root;M.animation_manifest={}
M.animation_support=true;M.raster_cache=true
assert(M.render_page(spec,{})==true,'cache hit bypasses all growth operations')
assert(M.animation.raster and not M.animation.plan)
local getenv=os.getenv
os.getenv=function(name) if name=='FLORAL_ANIMATION_PREPARE' then return '1' end return getenv(name) end
local missing={width=400,height=300,seed=2,text=spec.text}
assert(M.render_page(missing,{})==true,'measurement miss bypasses painting and fallback')
assert(M.animation_manifest[1].levels[1]==.5)
os.getenv=function(name) if name=='FLORAL_ANIMATION_PREPARE' then return nil end return getenv(name) end
assert(not pcall(M.render_page,missing,{}),'ordinary builds reject stale cache before planning')
M.frame.growth['growth duration']=1e300
assert(not pcall(M.render_page,spec,{}),'cache hit still checks duration limits')
os.getenv=getenv;kpse=oldkpse
os.remove(folder..'/sample-4.png')
assert(C.collect(a,spec,2)==nil,'the final poster must be cached before playback')
write(folder..'/sample-4.png',png)
a.stage=2;assert(C.collect(a,spec,2).stage==2,'display order selects the correct interval')
spec.seed=2;assert(C.collect(a,spec,2)==nil,'seed changes must invalidate cache')
spec.seed=1;assert(C.collect(a,spec,3)==nil,'sample-grid changes must invalidate cache')
spec.lines={{x0=70,y0=100,x1=200,y1=120}}
assert(C.collect(a,spec,2)==nil,'geometry changes must invalidate cache');spec.lines=nil
os.remove(folder..'/sample-3.png')
assert(C.collect(a,spec,2)==nil,'missing samples must invalidate playback')
write(folder..'/sample-3.png','broken')
assert(C.collect(a,spec,2)==nil,'broken sample headers must invalidate playback')
C.finish(a);assert(C.load(root..'-manifest').frames[1].signature==signature)
write(root..'/index.floral','os.execute("never execute cache data")')
a.animation_cache=nil;assert(C.collect(a,spec,2)==nil,'cache metadata must not access globals')
os.remove(root..'/index.floral');os.remove(folder..'/sample-1.png');os.remove(folder..'/sample-3.png')
for _,i in ipairs{0,2,4} do os.remove(folder..'/sample-'..i..'.png') end
assert(lfs.rmdir(folder));assert(lfs.rmdir(root));os.remove(root..'-manifest')
print('raster cache validity tests passed')
