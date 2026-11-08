-- Internal worker: export only missing raster samples from reusable plans.
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
local index={version=1,frames={}}
local jobs=assert(io.open(scratch..'/jobs.tsv','w'))
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
          Growth.stages(plan,frame.stages) -- keep the engine's resolution checks
        end
        local k=math.min(frame.stages,i//frame.steps+1)
        local first=k==1 and 0 or frame.levels[k-1]
        local t=first+(frame.levels[k]-first)*(i-(k-1)*frame.steps)/frame.steps
        local pdf=scratch..'/frame-'..id..'-sample-'..i..'.pdf'
        Pdf.write(pdf,Growth.render(plan,t),frame.spec.width,frame.spec.height)
        jobs:write(pdf,'\t',prefix,'\n'); count=count+1
      end
  end
  index.frames[id]={signature=frame.signature,stages=frame.stages,steps=frame.steps,dpi=dpi}
end
jobs:close()
local f=assert(io.open(scratch..'/index.floral','w'));f:write(Serial.encode(index),'\n');f:close()
print(string.format('Floral raster cache: %d missing samples across %d frames',count,#ids))
