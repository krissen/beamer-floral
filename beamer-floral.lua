-- Beamer owns frame identity and cross-overlay geometry; the engine stays generic.
local M = {}
local Serial = require('flora.serial')
local Settings = require('flora.settings')
-- These keys belong to the Beamer adapter, not to the botanical engine.
Settings.define('growth', function(v)
  if v=='off' or v=='overlays' or v=='timed' then return v end
  return nil, 'growth must be off, overlays or timed'
end)
Settings.define('growth duration', function(v)
  local n=tonumber(v)
  if n and n>0 and n<math.huge then return n end
  return nil, 'growth duration must be positive and finite (seconds)'
end)
Settings.define('growth fps', function(v)
  local n=tonumber(v)
  if n and n>=1 and n<=60 and n%1==0 then return n end
  return nil, 'growth fps must be an integer from 1 to 60'
end)
-- The stage layout: text in a narrow column on one side, the decoration in a
-- wide margin on the other. Beamer reads the text margins when a frame
-- starts and \setbeamersize is preamble-only, so the margins are assigned
-- at the start of each frame from that frame's own settings.
local stage_units={pt=1,mm=1,cm=1,['in']=1,bp=1,pc=1,dd=1,cc=1,ex=1,em=1}
local function stage_dimension(name)
  return function(v)
    v=tostring(v):gsub('^%s+',''):gsub('%s+$','')
    local number,rest=v:match('^(%d*%.?%d+)%s*(.*)$')
    if number and (stage_units[rest] or rest=='\\paperwidth' or rest=='\\paperheight') then
      return number..rest
    end
    return nil,name..' must be a positive length such as 62mm or 0.39\\paperwidth'
  end
end
Settings.define('stage', function(v)
  if v=='off' or v=='right' or v=='left' then return v end
  return nil,'stage must be off, right or left'
end)
Settings.define('stage width', stage_dimension('stage width'))
Settings.define('stage margin', stage_dimension('stage margin'))
local stage_defaults={['stage width']='0.39\\paperwidth',['stage margin']='12mm'}

-- Page classes that reuse one drawing per document instead of adapting.
local page_classes={title=1,section=2,content=3}
-- The value is a canonical string, not a table: settings merge tables key
-- by key, so a later reuse=none or a narrower list must replace it whole.
Settings.define('reuse', function(v)
  v=tostring(v):gsub('^%s*{',''):gsub('}%s*$','')
  local out={}
  for name in v:gmatch('[^,%s]+') do
    if name=='all' then for class in pairs(page_classes) do out[class]=true end
    elseif name=='none' then out={}
    elseif page_classes[name] then out[name]=true
    else return nil,'reuse must be none, all, or a list of title, section and content' end
  end
  local names={}
  for class in pairs(out) do names[#names+1]=class end
  table.sort(names)
  return #names>0 and table.concat(names,',') or 'none'
end)
local function reuse_set(value)
  local out={}
  for name in tostring(value or 'none'):gmatch('[^,]+') do
    if page_classes[name] then out[name]=true end
  end
  return out
end
local setting_fields={'layout','mix','ornaments','palette','spin','tune','header','doc_seed','reserve',
  'gilt','gilt_dpi','gilt_env','gilt_look','backdrop'}
-- Every setting the engine copies onto a spec (pattern, edge, outer, scale,
-- hero and any later key) is part of the frame's identity: a change misses
-- the geometry cache, and each drawing keys on its own spec.
do
  local known={}
  for _,k in ipairs(setting_fields) do known[k]=true end
  local extra={}
  for _,field in pairs(Settings.SPEC or {}) do if not known[field] then extra[#extra+1]=field end end
  table.sort(extra)
  for _,field in ipairs(extra) do setting_fields[#setting_fields+1]=field end
end
local growth_defaults={growth='off', ['growth duration']=8, ['growth fps']=20}

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
  local out={'beamer-floral-cache-2'}
  for id=1,M.count do
    local e=entries[id]
    if e then
      out[#out+1]='S\t'..id..'\t'..hex(e.signature)
      out[#out+1]='O\t'..id..'\t'..e.overlays
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
  assert(data:match('^beamer%-floral%-cache%-2\n'), 'cache version')
  local entries={}
  for line in data:gmatch('[^\n]+') do
    if line ~= 'beamer-floral-cache-2' then
      local p={}; for v in line:gmatch('[^\t]+') do p[#p+1]=v end
      local id=assert(tonumber(p[2])); assert(id>=1 and id%1==0)
      if p[1]=='S' then entries[id]={signature=unhex(p[3]),geometry={lines={}}}
      elseif p[1]=='O' then
        local n=assert(tonumber(p[3])); assert(n>=1 and n%1==0 and n<1e7)
        assert(entries[id]).overlays=n
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
  for _,e in pairs(entries) do assert(e.overlays, "missing overlay count") end
  return entries
end

function M.init(path)
  M.path=path; M.old=nil; M.previous={}; M.current={}; M.count=0; M.context_key=nil
  M.frame=nil; M.pending=nil; M.active_settings=nil; M.animation=nil
  M.animation_root=path:gsub('%.floral%-cache$','.floral-animation')
  M.animation_manifest={}; M.animation_cache=nil; M.pdf_actions=nil
  if kpse and kpse.record_input_file then kpse.record_input_file(path) end
  local f=io.open(path,'r')
  if f then
    M.old=f:read('*a'); f:close()
    local ok,result=pcall(decode,M.old)
    if ok then M.previous=result else M.old=nil end
  end
end

-- Called at the start of every frame, before Beamer reads the margins.
-- `body` is the collected frame body, or nil for a frame given as a command.
-- Title and section pages keep their own composition unless the frame asks
-- for the stage itself (\florathisframe{stage=...}); the body is scanned for
-- \titlepage and \sectionpage, the commands that set the page class for reuse.
function M.stage_begin(body,enabled)
  local set=Settings.merge(flora.settings,flora.once or {})
  local explicit=(flora.once or {}).stage~=nil
  local kind=set.stage
  M.stage_now=nil; M.stage_explicit=explicit
  if enabled and (kind=='right' or kind=='left') then
    local special=body and (body:find('\\titlepage%f[^%a]') or body:find('\\sectionpage%f[^%a]'))
    if explicit or not special then M.stage_now=kind end
  end
  if M.stage_now then
    local width=set['stage width'] or stage_defaults['stage width']
    local margin=set['stage margin'] or stage_defaults['stage margin']
    local left,right=margin,width
    if kind=='left' then left,right=width,margin end
    tex.sprint(string.format('\\floralstagemargins{%s}{%s}',left,right))
    M.staged=true
  elseif M.staged then
    tex.sprint('\\floralstagerestore')
    M.staged=false
  end
end
-- A title or section page the body scan missed (a wrapped \titlepage, or a
-- frame given as a command) was staged by default: say so.
function M.stage_check()
  if M.stage_now and not M.stage_explicit then
    tex.sprint('\\PackageWarning{beamer-floral}{A title or section page got the stage layout; use \\string\\florathisframe{stage=off} before this frame}')
  end
end

function M.context(start,continuation,enabled,plain)
  local key=tostring(start)..':'..tostring(continuation)
  if key ~= M.context_key then
    M.count=M.count+1; M.context_key=key; M.frame=nil; M.animation=nil
    M.enabled=enabled; M.plain=plain
  elseif enabled~=M.enabled then
    tex.error('beamer-floral: floraon/off must not change within one frame')
  end
end

-- A reused drawing's spec, from a page's prepared spec: one class drawing
-- for every page of the class with the same title state and settings.
local function reused_geometry(spec)
  local t=spec.text
  spec.lines={{x0=t.x0,y0=t.y0,x1=t.x1,y1=t.y1}}
  -- A title's width is not measured: a titled drawing keeps the top band
  -- clear across the text block, down to the title's height.
  local titled=spec.frametitle and true or false
  spec.frametitle=titled; spec.title=nil
  if not titled then spec.frametitle_height=nil end
  spec.header_right=titled and t.x1 or nil
  spec.body_top=spec.header=='body' and not M.plain
    and t.y1-(titled and spec.frametitle_height or 0) or nil
  spec.seed=flora.seed(spec.doc_seed,page_classes[M.frame.class])
  -- Alternating layouts need one drawing for each side.
  spec.page=spec.layout=='split' and 2-M.count%2 or 1
end
-- Whether the engine places and paints a page's running-head marks on
-- their own (compose.mark_layout); an older engine leaves reused pages
-- without a mark.
local function page_marks_supported()
  local ok,C=pcall(require,'flora.compose')
  return ok and type(C.mark_layout)=='function'
end
-- The engine's mark layout for a page spec, shared by every page whose spec
-- differs only in its measured lines (one per class and title state), and
-- its key.
local function mark_layout(page)
  local lines=page.lines
  page.lines=nil
  local key=Serial.encode(page)
  page.lines=lines
  M.mark_layouts=M.mark_layouts or {}
  local layout=M.mark_layouts[key]
  if not layout then
    layout=require('flora.compose').mark_layout(page)
    M.mark_layouts[key]=layout
  end
  return layout,key
end

function M.prepare(spec)
  if M.stage_now then spec.layout=M.stage_now end
  -- Untitled frames still have a running headline; plain frames do not.
  if spec.header=='body' and not M.plain and not spec.frametitle then
    spec.body_top=spec.body_top or spec.text.y1
  end
  -- The engine places its running-head mark below the head only where one
  -- is shown.
  spec.running_head=not M.plain
  local document=Serial.encode(flora.settings)
  local dimensions=Serial.encode({width=spec.width,height=spec.height,text=spec.text,header_y=spec.header_y})
  if not M.frame then
    M.frame={document=document, dimensions=dimensions, input_signature=M.input_signature,
      title_preset=M.page_title, section_preset=M.page_section,
      pending_signature=Serial.encode(M.pending or false), settings={}}
    for _,k in ipairs(setting_fields) do
      M.frame.settings[k]=copy(spec[k])
    end
    M.frame.growth={}
    local active=M.active_settings or flora.settings
    -- The frame's first-page settings, including a \florathisframe override
    -- that later overlays no longer carry; overlay drawings are keyed on it.
    M.frame.active=copy(active)
    for k,v in pairs(growth_defaults) do
      M.frame.growth[k]=active[k] or v
    end
    M.frame.seed=flora.seed(spec.doc_seed,M.count)
    local mark=(tex.count or {}).floralpageclass or 0
    M.frame.class=(M.page_title or mark==1) and 'title' or mark==2 and 'section' or 'content'
    -- A growing frame needs its own stages, and a frame with a caller's own
    -- renderer is drawn by it, so both keep their own drawings. So does a
    -- pattern frame: a reused drawing keeps the whole text block clear, which
    -- leaves a pattern almost nothing to fill, and patterns are cheap to draw.
    local listed=reuse_set(active['reuse'])[M.frame.class]
    local growing=M.frame.growth.growth~='off' and not M.handout
    local patterned=type(spec.pattern)=='table' and next(spec.pattern)~=nil
    M.frame.reuse=listed and not growing and not patterned and not M.custom_render or false
    -- One decision per frame, for test/check_reuse.lua.
    if texio and texio.write_nl then texio.write_nl('log',string.format('beamer-floral: frame %d class %s reuse %s',M.count,M.frame.class,
      M.frame.reuse and 'yes' or not listed and 'no (not listed)' or growing and 'no (growing)'
      or patterned and 'no (pattern)' or 'no (custom renderer)')..'\n') end
    M.frame.signature=Serial.encode({settings=M.frame.settings,width=spec.width,height=spec.height,
      text=spec.text,header_y=spec.header_y,input_signature=M.input_signature,growth=M.frame.growth,
      reuse=M.frame.reuse,class=M.frame.class})
  elseif document~=M.frame.document
      or (M.pending and Serial.encode(M.pending or false)~=M.frame.pending_signature)
      or dimensions~=M.frame.dimensions
      or M.input_signature~=M.frame.input_signature
      or Serial.encode(flora.reserve)~=Serial.encode(M.frame.settings.reserve) then
    tex.error('beamer-floral: floral settings and page dimensions must not change within one frame')
  end
  local signature=M.frame.signature
  local observed=geometry(spec)
  -- A reused drawing ignores measured content, so content cannot request a
  -- rerun. Only the frame title is kept, its height rounded up to 8 pt so
  -- descenders do not split one-line titles: the upper plant leaves that band
  -- clear, and it selects the drawing. The page's running-head mark is its
  -- own (render_reused): of the measured lines only those that decide it are
  -- kept, and in body mode the page's own body top, which is its ceiling.
  M.mark_geometry=nil
  if M.frame.reuse then
    local h=observed.frametitle and observed.frametitle_height
    local rounded=h and h>0 and math.ceil(h/8)*8 or nil
    local marks=page_marks_supported()
    local lines,body_top={},nil
    if marks then
      local page=copy(spec)
      for _,k in ipairs(setting_fields) do page[k]=copy(M.frame.settings[k]) end
      page.frametitle_height=rounded
      reused_geometry(page)
      if page.body_top then body_top=observed.body_top or page.body_top; page.body_top=body_top end
      local _,cut=mark_layout(page):place(observed.lines or {})
      lines=cut
    end
    observed={lines=lines,text=observed.text,frametitle=observed.frametitle and true or false,
      frametitle_height=rounded,body_top=body_top}
  end
  local entry=M.current[M.count]
  if not entry then entry={signature=signature,geometry={lines={}},overlays=0}; M.current[M.count]=entry end
  entry.geometry=merge(entry.geometry,observed)
  entry.overlays=entry.overlays+1
  local cached=M.previous[M.count]
  local selected=cached and cached.signature==signature and merge(cached.geometry,observed) or entry.geometry
  for k in pairs(fields) do spec[k]=copy(selected[k]) end
  for _,k in ipairs(setting_fields) do
    spec[k]=copy(M.frame.settings[k])
  end
  spec.seed=M.frame.seed
  -- split parity and any page-dependent composition must stay fixed as well.
  spec.page=M.count
  if M.frame.reuse then
    M.mark_geometry={lines=copy(spec.lines or {}),body_top=spec.body_top}
    reused_geometry(spec)
  end
  M.stage=entry.overlays
  M.stages=cached and cached.signature==signature and cached.overlays or M.stage
  -- A changed count is provisional until the next run. Never extrapolate.
  M.stages=math.max(M.stage,M.stages)
end

-- Growth is deliberately lazy: ordinary documents need neither the new
-- engine capability nor animate. The plan lives for one logical frame.
local Cache
local function raster_cache()
  if not Cache then Cache=dofile(kpse.find_file('beamer-floral-cache.lua','tex')) end
  return Cache
end

function M.render_page(spec,a)
  local growth=M.frame.growth
  if growth.growth=='off' or M.handout then return nil end
  if flora.render_page_version~=1 or type(flora.typeset_page)~='function' then
    tex.error('beamer-floral: growth needs tikz-flora with render_page_version=1')
    return nil
  end
  if growth.growth=='timed' and not M.animation_support then
    tex.error('beamer-floral: growth=timed needs \\usepackage{beamer-floral-animation} in the preamble')
    return nil
  end
  local Progression=require('flora.progression')
  if Progression.api_version~=1 then
    tex.error('beamer-floral: unsupported flora.progression API (need version 1)')
    return nil
  end
  local frame=M.frame
  local steps,seconds,raster,first,last
  if growth.growth=='timed' then
    seconds=growth['growth duration']/M.stages
    local samples=seconds*growth['growth fps']
    if seconds==0 or samples>2147483646 or 1/seconds==math.huge then
      tex.error('beamer-floral: growth duration exceeds animation numeric limits')
      return nil
    end
    steps=math.max(1,math.floor(samples+0.5))
    if M.gif_playback and not M.raster_cache then
      tex.error('beamer-floral: GIF playback needs the raster cache')
      return nil
    end
    if M.raster_cache then
      raster=raster_cache().collect(M,copy(spec),steps,seconds)
      if not raster then
        if os.getenv('FLORAL_ANIMATION_PREPARE')~='1' then
          tex.error('beamer-floral: raster animation cache missing or stale; run python3 tools/build_animation.py for this document, or select [vector]')
          return nil
        end
        -- Geometry was collected by prepare; this PDF is only a measurement
        -- intermediate. Returning true also suppresses the static fallback.
        return true
      end
    end
  end
  if not raster then
    local key=Serial.encode(spec)
    if frame.plan_key~=key then
      frame.plan=Progression.plan(copy(spec)); frame.plan_key=key
      frame.stage_count=nil
    end
    if frame.stage_count~=M.stages then
      frame.levels=Progression.stages(frame.plan,M.stages)
      frame.stage_count=M.stages
    end
    last=frame.levels[M.stage]
    if growth.growth=='overlays' then return Progression.render(frame.plan,last) end
    first=M.stage==1 and 0 or frame.levels[M.stage-1]
  end
  M.animation={plan=frame.plan,spec=copy(spec),args=copy(a),first=first,last=last,steps=steps,raster=raster,count=M.count}
  if raster and raster.gif then
    -- No animate environment and no JavaScript: the viewer plays the GIF.
    raster_cache().typeset_gif(M.animation)
    return true
  end
  -- N intervals have N+1 samples, including their exact endpoints.
  -- The final frame has no playback dwell; animate stops on that frame.
  tex.sprint(string.format(
    '\\begingroup\\def\\floralanimationlast{%d}\\floralanimationclock\\begin{animateinline}[method=ocg,autoplay,autopause=false,autoresume=false,loop=false,palindrome=false,controls=false,nomouse,poster=last,label=floral-%d-%d]{%.12g}',
    steps,M.count,M.stage,steps/seconds))
  for i=0,steps do
    if i>0 then tex.sprint('\\newframe') end
    tex.sprint(string.format('\\directlua{beamer_floral.paint_animation(%d)}',i))
  end
  tex.sprint('\\end{animateinline}\\endgroup')
  return true
end

-- One form, drawn on any number of pages. Clips and bands are applied per page.
local function form_painter(holder,spec)
  local Paint=require('flora.paint')
  local pt=require('flora.compose').page(copy(spec))
  local forms,resources=Paint.forms({{chunks={pt:body()}}},spec.width,spec.height)
  holder.pt,holder.forms,holder.resources=pt,forms,resources
end
local function draw_form(shared)
  local painter=require('flora.paint').new{backend='pdf'}
  painter.defs=shared.pt.defs
  painter.xobjects=shared.forms
  painter.pdf_resources=shared.resources
  painter.coverage=shared.pt.coverage
  painter.count=shared.pt.count
  painter:emit('/'..shared.forms[1].name..' Do')
  return painter
end

-- A drawing from the engine's page cache: the cached one-page PDF is
-- written to this PDF once and drawn on every page that uses it, and later
-- compiles embed the file instead of composing it again. The key is the
-- engine's own: the prepared spec, the active settings, tune and the engine
-- code.
local function cached_image(spec)
  local ok,Cache=pcall(require,'flora.cache')
  if not ok or type(Cache.page)~='function' or not (img and img.scan and img.immediatewrite) then return nil end
  local set=(M.frame and M.frame.active) or M.active_settings or flora.settings
  if set.cache==false then return nil end
  local file,e,hit=Cache.page(copy(spec),set,pdf.getcompresslevel and pdf.getcompresslevel() or 6)
  if not file then return nil end
  local image=img.scan({filename=file})
  img.immediatewrite(image)
  return {objnum=image.objnum,count=e.count or 0,coverage=e.coverage or 0,hit=hit,
    name='flreuse'..image.objnum}
end
-- The cached drawing, or a form painted in this run when the cache is off
-- or unavailable.
local function cached_or_form(spec)
  local drawing=cached_image(spec)
  if not drawing then drawing={}; form_painter(drawing,spec) end
  return drawing
end
-- A drawing's Form or image XObject: its resource name and object number.
local function xobject(drawing)
  if drawing.objnum then return drawing.name,drawing.objnum end
  local f=drawing.forms[1]
  return f.name,f.object
end
-- A drawing, then a page's own marks over it: two XObjects, each carrying
-- its own resources, so the page names only the two.
local function draw_drawing(drawing,marks)
  if marks then
    local painter=require('flora.paint').new{backend='pdf'}
    local refs,ops,defs={},{},{}
    for _,d in ipairs({drawing,marks}) do
      local name,object=xobject(d)
      refs[#refs+1]='/'..name..' '..object..' 0 R'
      ops[#ops+1]='/'..name..' Do'
      if d.pt then for _,def in ipairs(d.pt.defs) do defs[#defs+1]=def end end
    end
    painter.defs=defs
    painter.xobjects={}
    painter.pdf_resources='/XObject << '..table.concat(refs,' ')..' >>'
    painter.coverage=drawing.coverage or (drawing.pt and drawing.pt.coverage)
    painter.count=(drawing.count or (drawing.pt and drawing.pt.count) or 0)
      +(marks.count or (marks.pt and marks.pt.count) or 0)
    painter:emit(table.concat(ops,' '))
    return painter
  end
  if not drawing.objnum then return draw_form(drawing) end
  local painter=require('flora.paint').new{backend='pdf'}
  painter.xobjects={}
  painter.pdf_resources='/XObject << /'..drawing.name..' '..drawing.objnum..' 0 R >>'
  painter.coverage=drawing.coverage
  painter.count=drawing.count
  painter:emit('/'..drawing.name..' Do')
  return painter
end

-- Overlays of a static frame show the same flora: one drawing per frame,
-- from the page cache, drawn on each overlay page. The prepared spec carries
-- the frame's merged geometry, frame settings, seed and page. Neither the
-- overlay step nor the overlay count is keyed: every overlay of a converged
-- frame gets the same spec, and a count change that leaves the merged
-- geometry unchanged leaves the drawing unchanged. Any change that alters
-- the drawing changes the spec or the settings and misses the cache.
function M.render_static(spec)
  local frame=M.frame
  local key=Serial.encode(spec)
  if frame.static_key~=key then
    frame.static=cached_or_form(spec)
    frame.static_key=key
    texio.write_nl('log',string.format('beamer-floral: frame %d static flora %s',M.count,
      frame.static.hit and 'from the cache' or frame.static.objnum and 'grown and cached' or 'painted'))
  end
  return draw_drawing(frame.static)
end

-- A reused page's own running-head marks, painted over the class drawing:
-- placed by the engine from this page's measured lines (and in body mode
-- its body top, which also sets the page inset) with the drawing's layout,
-- foot runs, clips and settings, as the adaptive page would place them. The mark's kind comes from the
-- drawing's seed, so every page of a class shows the same kind. Pages
-- whose marks fall alike share one drawing of them, cached as the flora is.
-- nil when the page holds no mark or the engine cannot paint marks alone.
local function reused_marks(spec)
  local geometry=M.mark_geometry
  if not geometry or not page_marks_supported() then return nil end
  local page=copy(spec)
  if geometry.body_top and page.body_top then page.body_top=geometry.body_top end
  local layout,key=mark_layout(page)
  local marks=layout:place(geometry.lines)
  -- For test/check_reuse_mark.lua: the count, then each mark's size and
  -- centre, one short line each.
  texio.write_nl('log',string.format('beamer-floral: frame %d reused page marks %d',M.count,#marks))
  for _,m in ipairs(marks) do
    texio.write_nl('log',string.format('beamer-floral: frame %d reused page mark %.2f pt at %.2f',M.count,m.size,m.y))
  end
  if #marks==0 then return nil end
  page.marks_only=marks
  M.reused_marks=M.reused_marks or {}
  key=key..Serial.encode(marks)
  local drawing=M.reused_marks[key]
  if not drawing then
    drawing=cached_or_form(page)
    M.reused_marks[key]=drawing
  end
  return drawing
end

-- A reused drawing is one PDF object per class, title state, settings and
-- page geometry.
function M.render_reused(spec)
  M.reused=M.reused or {}
  local key=Serial.encode(spec)
  local reused=M.reused[key]
  if not reused then
    reused=cached_or_form(spec)
    M.reused[key]=reused
    texio.write_nl('log','beamer-floral: drew reused flora for class '..M.frame.class
      ..(reused.hit and ' from the cache' or ''))
  end
  return draw_drawing(reused,reused_marks(spec))
end

function M.paint_animation(i)
  local animation=assert(M.animation,'missing floral animation')
  if animation.raster then
    return raster_cache().typeset(animation,i)
  end
  local t=animation.first+(animation.last-animation.first)*i/animation.steps
  local pt=require('flora.progression').render(animation.plan,t)
  flora.typeset_page(pt,animation.spec,animation.args)
end

-- \floralgifmatte: the page colour the GIF frames are composited against.
function M.check_matte(value)
  if not value:match('^%x%x%x%x%x%x$') then
    tex.error('beamer-floral: \\floralgifmatte needs six hexadecimal digits, as in FFFFFF')
    return M.gif_matte
  end
  return value:upper()
end

function M.note_animation(id)
  if not M.pdf_actions then M.pdf_actions=dofile(kpse.find_file('beamer-floral-pdf.lua','tex')) end
  M.pdf_actions.note(id)
end

function M.finish()
  if M.pdf_actions then M.pdf_actions.finish() end
  if M.animation_support then raster_cache().finish(M) end
  if kpse and kpse.record_output_file then kpse.record_output_file(M.path) end
  local data=encode(M.current)
  if data~=M.old then
    local f=assert(io.open(M.path..'.tmp','w')); f:write(data); f:close()
    assert(os.rename(M.path..'.tmp',M.path))
    tex.sprint('\\PackageWarningNoLine{beamer-floral}{Floral geometry or overlay count changed. Rerun to get stable overlays}')
  end
end

M._merge=merge; M._decode=decode; M._encode=encode
return M
