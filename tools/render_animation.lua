-- Internal worker: export only missing raster samples from reusable plans.
-- It also lists the GIFs of GIF playback in gifs.tsv, one line per interval:
-- sample folder, first sample, steps, rate in milli-fps, matte, output path.
-- Paths arrive as argv, never as executable Lua or shell fragments.
local lua_root,manifest_path,cache_root,scratch,dpi=arg[1],arg[2],arg[3],arg[4],tonumber(arg[5])
assert(lua_root and manifest_path and cache_root and scratch and dpi)
package.path=lua_root..'/?.lua;'..package.path
local Serial=require('flora.serial')
local Paint=require('flora.paint')
local Growth=require('flora.progression')
local Pdf=require('flora.pdfout')
local lfs=require('lfs')
local function load(path)
  local f=io.open(path,'rb'); if not f then return nil end
  local data=f:read('a'); f:close(); return Serial.decode(data)
end
local manifest=assert(load(manifest_path),'missing animation manifest')
assert(manifest.version==1 and type(manifest.frames)=='table','unsupported animation manifest')
assert(Growth.api_version==1,'unsupported progression API (need version 1)')
local index={version=1,frames={}}
local jobs=assert(io.open(scratch..'/jobs.tsv','w'))
local gifs={}
local count=0
local ids={};for id in pairs(manifest.frames) do ids[#ids+1]=id end;table.sort(ids)
for _,id in ipairs(ids) do
  local frame=manifest.frames[id]
  assert(type(id)=='number' and id%1==0 and id>0)
  assert(frame.signature:match('^%x+$') and #frame.signature==32,'invalid cache signature')
  assert(frame.stages>=1 and frame.stages%1==0 and frame.steps>=1 and frame.steps%1==0)
  assert(#frame.levels==frame.stages,'incomplete stage levels')
  local folder=cache_root..'/'..frame.signature..'-'..dpi
  if not lfs.attributes(folder) then assert(lfs.mkdir(folder)) end
  local plan
  for i=0,frame.stages*frame.steps do
      local prefix=folder..'/sample-'..i
      local f=io.open(prefix..'.png','rb')
      local exists=f and f:read(8)=='\137PNG\r\n\26\n'
      if f then f:close() end
      if not exists then
        if not plan then
          Paint.reset_resources();plan=Growth.plan(frame.spec)
          local levels=Growth.stages(plan,frame.stages)
          for k=1,frame.stages do
            assert(frame.levels[k]==levels[k],'manifest stage levels disagree with progression API')
          end
        end
        local k=math.min(frame.stages,i//frame.steps+1)
        local first=k==1 and 0 or frame.levels[k-1]
        local t=first+(frame.levels[k]-first)*(i-(k-1)*frame.steps)/frame.steps
        local pdf=scratch..'/frame-'..id..'-sample-'..i..'.pdf'
        Pdf.write(pdf,Growth.render(plan,t),frame.spec.width,frame.spec.height)
        jobs:write(pdf,'\t',prefix,'\n'); count=count+1
      end
  end
  if frame.gif~=nil then
    local gif=frame.gif
    assert(type(gif)=='table' and type(gif.rate_milli)=='number' and gif.rate_milli>=1 and gif.rate_milli%1==0,
      'invalid GIF playback rate')
    assert(type(gif.matte)=='string' and gif.matte:match('^%x%x%x%x%x%x$'),'invalid GIF matte colour')
    for k=1,frame.stages do
      -- The name must match C.gif_name in beamer-floral-cache.lua.
      gifs[#gifs+1]=string.format('%s\t%d\t%d\t%d\t%s\t%s/interval-%d-r%d-m%s.gif',
        folder,(k-1)*frame.steps,frame.steps,gif.rate_milli,gif.matte,folder,k,gif.rate_milli,gif.matte)
    end
  end
  index.frames[id]={signature=frame.signature,stages=frame.stages,steps=frame.steps,dpi=dpi}
end
jobs:close()
local g=assert(io.open(scratch..'/gifs.tsv','w'));g:write(table.concat(gifs,'\n'),#gifs>0 and '\n' or '');g:close()
local f=assert(io.open(scratch..'/index.floral','w'));f:write(Serial.encode(index),'\n');f:close()
print(string.format('Floral raster cache: %d missing samples across %d frames',count,#ids))
