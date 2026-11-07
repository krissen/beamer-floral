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
assert(C.collect(a,spec,2).stage==1,'current cache must be usable')
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
assert(lfs.rmdir(folder));assert(lfs.rmdir(root));os.remove(root..'-manifest')
print('raster cache validity tests passed')
