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
-- GIF playback: the same samples plus the interval's GIF.
for _,i in ipairs{1,3} do write(folder..'/sample-'..i..'.png',png) end
a.gif_playback=true;a.gif_matte='FFFFFF';a.animation_cache=nil;a.stage=1
assert(C.collect(a,spec,2,1)==nil,'GIF mode must reject a cache without the GIF')
assert(a.animation_manifest[1].gif.rate_milli==2000 and a.animation_manifest[1].gif.matte=='FFFFFF')
assert(a.animation_manifest[1].signature==signature,'GIF info must not change the cache signature')
local gif=folder..'/interval-1-r2000-mFFFFFF-e2.gif'
write(folder..'/interval-1-r2000-mFFFFFF.gif','GIF89a'..string.rep('\0',32))
assert(C.collect(a,spec,2,1)==nil,'a GIF from an older encoder must not be reused')
os.remove(folder..'/interval-1-r2000-mFFFFFF.gif')
assert(a.animation_manifest[1].gif.encoder==C.gif_encoder)
write(gif,'broken');assert(C.collect(a,spec,2,1)==nil,'GIF mode must reject a file that is no GIF')
write(gif,'GIF89a'..string.rep('\0',32))
local hit=assert(C.collect(a,spec,2,1),'GIF mode must accept a cache with the GIF')
assert(hit.gif==gif and hit.gif_relative==root:match('[^/]+$')..'/'..signature..'-144/interval-1-r2000-mFFFFFF-e2.gif')
assert(C.collect(a,spec,2,0.5)==nil,'another rate needs another GIF')
a.gif_matte='102030';assert(C.collect(a,spec,2,1)==nil,'another matte needs another GIF')
a.gif_matte='FFFFFF';a.stage=2;assert(C.collect(a,spec,2,1)==nil,'each interval has its own GIF')
a.gif_playback=false;a.stage=1;os.remove(gif)
assert(C.collect(a,spec,2).gif==nil,'raster mode ignores GIFs')
-- Emission: one image and one full-page Movie annotation, no animate.
a.gif_playback=true;write(gif,'GIF89a'..string.rep('\0',32))
local emitted,page={}
tex.sprint=function(s) emitted[#emitted+1]=s end
local previous=package.loaded['flora.paint']
package.loaded['flora.paint']={new=function() return {emit=function(_,s) page=(page or '')..s end} end}
flora.typeset_page=function() end
local animation={spec=spec,args={},steps=2,count=7,raster=C.collect(a,spec,2,1)}
C.typeset_gif(animation)
assert(page:find('sample-0.png',1,true),'the start sample is the static image')
assert(page:find('/Subtype /Movie',1,true) and page:find('/T (floral-7-1)',1,true))
assert(page:find('/Mode /Once /ShowControls false',1,true))
assert(page:find('width 400.00000000pt height 300.00000000pt',1,true),'the annotation covers the page')
local target=page:match('/Movie << /F %(\\detokenize{(.-)}%)')
assert(target==root:match('[^/]+$')..'/'..signature..'-144/interval-1-r2000-mFFFFFF-e2.gif','relative path, no directories above the cache')
for _,bad in ipairs{'a(b','a)b','a\\b','a%b'} do
  animation.raster.gif_relative=bad..'/x.gif';assert(not pcall(C.typeset_gif,animation),bad)
end
-- Embedded: one macro call carries file, name, page size and the physical page.
page=nil;animation.raster.embed=true;animation.raster.gif=gif
animation.raster.gif_relative=root:match('[^/]+$')..'/'..signature..'-144/interval-1-r2000-mFFFFFF-e2.gif'
C.typeset_gif(animation)
assert(page:find('\\floralembedgif{\\detokenize{'..gif..'}}{\\detokenize{interval-1-r2000-mFFFFFF-e2.gif}}{400.00000000pt}{300.00000000pt}{1}',1,true),page)
assert(not page:find('/Movie',1,true),'no Movie annotation for embedded GIFs')
for _,bad in ipairs{folder..'/a(b-e2.gif',folder..'/a{b-e2.gif',folder..'/a#b-e2.gif'} do
  animation.raster.gif=bad;assert(not pcall(C.typeset_gif,animation),bad)
end
package.loaded['flora.paint']=previous;tex.sprint=function() end
os.remove(gif);a.gif_playback=false
-- Through the adapter: a GIF interval emits no animate environment.
local sprinted=0
tex.sprint=function() sprinted=sprinted+1 end
M.frame.growth['growth duration']=1;M.gif_playback=true;M.stage=1;M.animation_cache=nil;M.animation_manifest={}
local viagif=folder..'/interval-1-r4000-mFFFFFF-e2.gif'
os.getenv=function(name) if name=='FLORAL_ANIMATION_PREPARE' then return nil end return getenv(name) end
assert(not pcall(M.render_page,spec,{}),'GIF mode without the GIF is a missing cache')
write(viagif,'GIF89a'..string.rep('\0',32))
local lines={};package.loaded['flora.paint']={new=function() return {emit=function(_,t) lines[#lines+1]=t end} end}
assert(M.render_page(spec,{})==true);assert(#lines==2 and lines[2]:find('/Subtype /Movie',1,true))
M.gif_embed=true;lines={};assert(M.render_page(spec,{})==true);assert(#lines==2 and lines[2]:find('floralembedgif',1,true),'embedded mode');M.gif_embed=false
assert(M.animation.raster.gif==viagif);assert(sprinted==0,'no animate environment for GIF intervals')
package.loaded['flora.paint']=nil;os.getenv=getenv;os.remove(viagif);M.gif_playback=false
C.finish(a);assert(C.load(root..'-manifest').frames[1].signature==signature)
write(root..'/index.floral','os.execute("never execute cache data")')
a.animation_cache=nil;assert(C.collect(a,spec,2)==nil,'cache metadata must not access globals')
os.remove(root..'/index.floral');os.remove(folder..'/sample-1.png');os.remove(folder..'/sample-3.png')
for _,i in ipairs{0,2,4} do os.remove(folder..'/sample-'..i..'.png') end
assert(lfs.rmdir(folder));assert(lfs.rmdir(root));os.remove(root..'-manifest')
print('raster cache validity tests passed')
