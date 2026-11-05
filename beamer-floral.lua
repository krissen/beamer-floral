-- Beamer owns frame identity and cross-overlay geometry; the engine stays generic.
local M = {}
local Serial = require('flora.serial')
local function copy(t)
  if type(t) ~= 'table' then return t end
  local out = {}; for k,v in pairs(t) do out[k] = copy(v) end; return out
end
local function hex(s) return (s:gsub('.', function(c) return string.format('%02x', c:byte()) end)) end
local function unhex(s)
  assert(s:match('^%x*$') and #s % 2 == 0, 'invalid cache signature')
  return (s:gsub('%x%x', function(c) return string.char(tonumber(c,16)) end))
end
local rects = {text=true, title=true}
local maxima = {frametitle_height=true, header_right=true, frametitle=true}
local fields = {lines=true, text=true, title=true, frametitle_height=true,
  header_right=true, frametitle=true, body_top=true}
local function boxunion(a,b)
  if not a then return copy(b) end
  return {x0=math.min(a.x0,b.x0), y0=math.min(a.y0,b.y0),
    x1=math.max(a.x1,b.x1), y1=math.max(a.y1,b.y1)}
end
local function geometry(spec)
  local out={lines={}}
  for k in pairs(fields) do if spec[k] ~= nil then out[k]=copy(spec[k]) end end
  return out
end
local function merge(a,b)
  local out=copy(a or {lines={}})
  local seen={}
  for _,r in ipairs(out.lines) do seen[Serial.encode(r)]=true end
  for _,r in ipairs(b.lines or {}) do
    local key=Serial.encode(r)
    if not seen[key] then out.lines[#out.lines+1]=copy(r); seen[key]=true end
  end
  table.sort(out.lines,function(x,y) return Serial.encode(x)<Serial.encode(y) end)
  for k in pairs(fields) do
    if k ~= 'lines' and b[k] ~= nil then
      if rects[k] then out[k]=boxunion(out[k],b[k])
      elseif k=='frametitle' then out[k]=out[k] or b[k]
      elseif maxima[k] then out[k]=math.max(out[k] or b[k],b[k])
      else out[k]=math.min(out[k] or b[k],b[k]) end
    end
  end
  return out
end

-- Cache is numeric TSV plus an opaque hex signature. Never execute cached code.
local function encode(entries)
  local out={'beamer-floral-cache-1'}
  for id=1,M.count do
    local e=entries[id]
    if e then
      out[#out+1]='S\t'..id..'\t'..hex(e.signature)
      local keys={}; for k in pairs(e.geometry) do keys[#keys+1]=k end; table.sort(keys)
      local function row(k,r)
        out[#out+1]=table.concat({'G',id,k,string.format('%.17g',r.x0),string.format('%.17g',r.y0),
          string.format('%.17g',r.x1),string.format('%.17g',r.y1)},'\t')
      end
      for _,k in ipairs(keys) do
        local v=e.geometry[k]
        if k=='lines' then for _,r in ipairs(v) do row(k,r) end
        elseif rects[k] then row(k,v)
        else out[#out+1]=table.concat({'V',id,k,type(v)=='boolean' and (v and '1' or '0') or string.format('%.17g',v)},'\t') end
      end
    end
  end
  return table.concat(out,'\n')..'\n'
end
local function decode(data)
  assert(data:match('^beamer%-floral%-cache%-1\n'), 'cache version')
  local entries={}
  for line in data:gmatch('[^\n]+') do
    if line ~= 'beamer-floral-cache-1' then
      local p={}; for v in line:gmatch('[^\t]+') do p[#p+1]=v end
      local id=assert(tonumber(p[2])); assert(id>=1 and id%1==0)
      if p[1]=='S' then entries[id]={signature=unhex(p[3]),geometry={lines={}}}
      else
        local g=assert(entries[id]).geometry; local k=p[3]; assert(fields[k])
        local function number(i) local n=assert(tonumber(p[i])); assert(n==n and math.abs(n)<1e12); return n end
        if p[1]=='G' then
          assert(k=='lines' or rects[k]); local r={x0=number(4),y0=number(5),x1=number(6),y1=number(7)}
          assert(r.x0<=r.x1 and r.y0<=r.y1,'reversed cache rectangle')
          if k=='lines' then g.lines[#g.lines+1]=r else g[k]=r end
        else
          assert(p[1]=='V' and not rects[k] and k~='lines')
          if k=='frametitle' then g[k]=number(4)==1 else g[k]=number(4) end
        end
      end
    end
  end
  return entries
end

function M.init(path)
  M.path=path; M.old=nil; M.previous={}; M.current={}; M.count=0; M.context_key=nil
  M.frame=nil; M.pending=nil
  if kpse and kpse.record_input_file then kpse.record_input_file(path) end
  local f=io.open(path,'r')
  if f then
    M.old=f:read('*a'); f:close()
    local ok,result=pcall(decode,M.old)
    if ok then M.previous=result else M.old=nil end
  end
end

function M.context(start,continuation,enabled,plain)
  local key=tostring(start)..':'..tostring(continuation)
  if key ~= M.context_key then
    M.count=M.count+1; M.context_key=key; M.frame=nil; M.enabled=enabled; M.plain=plain
  elseif enabled~=M.enabled then
    tex.error('beamer-floral: floraon/off must not change within one frame')
  end
end

function M.prepare(spec)
  -- Untitled frames still have a running headline; plain frames do not.
  if spec.header=='body' and not M.plain and not spec.frametitle then
    spec.body_top=spec.body_top or spec.text.y1
  end
  local document=Serial.encode(flora.settings)
  local dimensions=Serial.encode({width=spec.width,height=spec.height,text=spec.text,header_y=spec.header_y})
  if not M.frame then
    M.frame={document=document, dimensions=dimensions, input_signature=M.input_signature, settings={}}
    for _,k in ipairs({'layout','mix','ornaments','palette','spin','tune','header','doc_seed','reserve'}) do
      M.frame.settings[k]=copy(spec[k])
    end
    M.frame.seed=flora.seed(spec.doc_seed,M.count)
    M.frame.signature=Serial.encode({settings=M.frame.settings,width=spec.width,height=spec.height,
      text=spec.text,header_y=spec.header_y,input_signature=M.input_signature})
  elseif document~=M.frame.document or M.pending or dimensions~=M.frame.dimensions
      or M.input_signature~=M.frame.input_signature
      or Serial.encode(flora.reserve)~=Serial.encode(M.frame.settings.reserve) then
    tex.error('beamer-floral: floral settings and page dimensions must not change within one frame')
  end
  local signature=M.frame.signature
  local observed=geometry(spec)
  local entry=M.current[M.count]
  if not entry then entry={signature=signature,geometry={lines={}}}; M.current[M.count]=entry end
  entry.geometry=merge(entry.geometry,observed)
  local cached=M.previous[M.count]
  local selected=cached and cached.signature==signature and merge(cached.geometry,observed) or entry.geometry
  for k in pairs(fields) do spec[k]=copy(selected[k]) end
  for _,k in ipairs({'layout','mix','ornaments','palette','spin','tune','header','doc_seed','reserve'}) do
    spec[k]=copy(M.frame.settings[k])
  end
  spec.seed=M.frame.seed
  -- split parity and any page-dependent composition must stay fixed as well.
  spec.page=M.count
end

function M.finish()
  if kpse and kpse.record_output_file then kpse.record_output_file(M.path) end
  local data=encode(M.current)
  if data~=M.old then
    local f=assert(io.open(M.path..'.tmp','w')); f:write(data); f:close()
    assert(os.rename(M.path..'.tmp',M.path))
    tex.sprint('\\PackageWarningNoLine{beamer-floral}{Floral geometry changed. Rerun to get stable overlays}')
  end
end

M._merge=merge; M._decode=decode; M._encode=encode
return M
