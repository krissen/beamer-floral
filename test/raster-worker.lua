-- Worker validation and failure publication, without botanical rendering.
-- texlua test/raster-worker.lua /path/to/tikz-flora
package.path=arg[1]..'/lua/?.lua;'..package.path
local Serial=require('flora.serial')
local lfs=require('lfs')
local root=os.tmpname();os.remove(root);assert(lfs.mkdir(root))
assert(lfs.mkdir(root..'/scratch'))
local signature=string.rep('a',32)
local folder=root..'/'..signature..'-144';assert(lfs.mkdir(folder))
local function write(path,data) local f=assert(io.open(path,'wb'));f:write(data);f:close() end
local frame={signature=signature,stages=2,steps=1,levels={.5,1},spec={width=400,height=300}}
local plans,renders=0,0
local fail=false
package.loaded['flora.paint']={reset_resources=function() end}
package.loaded['flora.progression']={api_version=1,
  plan=function() plans=plans+1;return {} end,
  stages=function() return {.5,1} end,
  render=function(_,t) assert(not fail,'injected rendering failure');renders=renders+1;return t end}
package.loaded['flora.pdfout']={write=function(path,t) write(path,tostring(t)) end}
local function run()
  write(root..'/manifest',Serial.encode{version=1,frames={frame}})
  arg={'unused',root..'/manifest',root,root..'/scratch','144'}
  return pcall(dofile,'tools/render_animation.lua')
end
assert(run());assert(plans==1 and renders==3)
local f=assert(io.open(root..'/scratch/frame-1-sample-1.pdf'));assert(f:read('a')=='0.5');f:close()
local function slurp(path) local h=assert(io.open(path,'rb'));local d=h:read('a');h:close();return d end
assert(slurp(root..'/scratch/gifs.tsv')=='','no GIF playback lists no GIFs')
frame.gif={rate_milli=2000,matte='FFFFFF',encoder='e3'}
assert(run())
assert(slurp(root..'/scratch/gifs.tsv')==
  folder..'\t0\t1\t2000\tFFFFFF\t'..folder..'/interval-1-r2000-mFFFFFF-e3.gif\t400,300\t\n'..
  folder..'\t1\t1\t2000\tFFFFFF\t'..folder..'/interval-2-r2000-mFFFFFF-e3.gif\t400,300\t\n','one GIF per interval')
-- Reservations travel with every interval: the GIF is an annotation, the page's clip cannot reach it.
frame.spec.reserve={{0,0,25,100},{10.5,20,30,40.25}}
assert(run())
assert(slurp(root..'/scratch/gifs.tsv'):find('\t400,300\t0,0,25,100;10.5,20,30,40.25\n',1,true),'reserved rectangles reach gifs.tsv')
frame.spec.reserve=nil
frame.gif={rate_milli=2000,matte='nothex',encoder='e3'};os.remove(root..'/scratch/gifs.tsv')
assert(not run(),'invalid matte must fail');assert(not lfs.attributes(root..'/scratch/gifs.tsv'))
frame.gif=nil
os.remove(root..'/scratch/index.floral')
frame.levels={.4,1};assert(not run(),'worker must compare API levels')
assert(not lfs.attributes(root..'/scratch/index.floral'))
frame.levels={.5,1};fail=true
assert(not run(),'render failure propagates');assert(not lfs.attributes(root..'/scratch/index.floral'))
fail=false
local png='\137PNG\r\n\26\n'
for i=0,2 do write(folder..'/sample-'..i..'.png',png) end
local before=plans
assert(run());assert(plans==before,'warm worker must not plan')
os.remove(folder..'/sample-1.png')
assert(run());assert(plans==before+1,'partial cache plans only missing samples')
for i=0,2 do os.remove(folder..'/sample-'..i..'.png');os.remove(root..'/scratch/frame-1-sample-'..i..'.pdf') end
os.remove(root..'/scratch/index.floral');os.remove(root..'/scratch/gifs.tsv');os.remove(root..'/scratch/jobs.tsv');os.remove(root..'/manifest')
assert(lfs.rmdir(folder));assert(lfs.rmdir(root..'/scratch'));assert(lfs.rmdir(root))
print('raster worker contract tests passed')
