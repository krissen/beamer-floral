-- Raster cache metadata. Files use the engine's plain-data serializer.
local Serial=require('flora.serial')
local C={version=1}
local function read(path)
  local f=io.open(path,'rb'); if not f then return nil end
  local s=f:read('a'); f:close(); return s
end
function C.load(path)
  local s=read(path); if not s then return nil end
  local ok,t=pcall(Serial.decode,s)
  if ok and type(t)=='table' and t.version==C.version then return t end
end
local function write(path,value)
  local data=Serial.encode(value)..'\n'
  if data==read(path) then return end
  local f=assert(io.open(path..'.tmp','w')); f:write(data); f:close()
  assert(os.rename(path..'.tmp',path))
end
local function signature(record)
  local ok,engine=pcall(require,'flora.cache')
  assert(ok and type(engine.key)=='function','raster playback needs the pinned tikz-flora cache API')
  return assert(engine.key({raster_cache_version=C.version,frame=record}),
    'cannot identify engine sources for raster playback')
end
-- Encoder version of the GIF files. Raise it whenever the builder's output
-- changes, so caches made by an older encoder are rebuilt, not reused.
C.gif_encoder='e2'
function C.gif_name(stage,rate_milli,matte,encoder)
  return string.format('interval-%d-r%d-m%s-%s.gif',stage,rate_milli,matte,encoder or C.gif_encoder)
end
-- seconds is one interval's duration; only GIF playback needs it.
function C.collect(adapter,spec,steps,seconds)
  -- Progression API v1 defines equal-area levels as k/n. Plan-dependent
  -- resolution checks belong to the export worker, only on a cache miss.
  local levels={}
  for k=1,adapter.stages do levels[k]=k/adapter.stages end
  local record={spec=spec,stages=adapter.stages,steps=steps,levels=levels}
  record.signature=signature(record)
  -- Set after the signature: the GIF description names a file inside the
  -- sample folder and must not change the folder's name.
  local gif
  if adapter.gif_playback then
    assert(type(seconds)=='number' and seconds>0,'GIF playback needs the interval duration')
    gif={rate_milli=math.floor(steps/seconds*1000+0.5),matte=adapter.gif_matte or 'FFFFFF',encoder=C.gif_encoder}
    assert(gif.rate_milli>=1,'GIF playback rate is too low')
    record.gif=gif
  end
  adapter.animation_manifest[adapter.count]=record
  if not adapter.animation_cache then
    local path=adapter.animation_root..'/index.floral'
    if kpse and kpse.record_input_file then kpse.record_input_file(path) end
    adapter.animation_cache=C.load(path) or {version=C.version,frames={}}
  end
  local cached=(adapter.animation_cache.frames or {})[adapter.count]
  if not cached or cached.signature~=record.signature or cached.steps~=steps
      or cached.stages~=adapter.stages then return nil end
  if type(cached.dpi)~='number' or cached.dpi<36 or cached.dpi>600 then return nil end
  local directory=record.signature..'-'..cached.dpi..'/'
  local prefix=adapter.animation_root..'/'..directory..'sample-'
  -- Keep playback, interval boundaries and the static poster on the same
  -- rendering path; switching to a heavy vector endpoint can flash in Reader.
  for i=0,steps*adapter.stages do
      local f=io.open(prefix..i..'.png','rb')
      if not f then return nil end
      local signature=f:read(8); f:close()
      if signature~='\137PNG\r\n\26\n' then return nil end
  end
  local result={prefix=prefix,steps=steps,stage=adapter.stage}
  if gif then
    local name=C.gif_name(adapter.stage,gif.rate_milli,gif.matte)
    local path=adapter.animation_root..'/'..directory..name
    local f=io.open(path,'rb')
    if not f then return nil end
    local head=f:read(4); f:close()
    if head~='GIF8' then return nil end
    result.gif=path
    result.embed=adapter.gif_embed and true or false
    -- Viewers resolve the movie file against the directory of the PDF.
    result.gif_relative=adapter.animation_root:match('[^/\\]+$')..'/'..directory..name
  end
  return result
end
function C.finish(adapter)
  local path=adapter.animation_root..'-manifest'
  if kpse and kpse.record_output_file then kpse.record_output_file(path) end
  write(path,{version=C.version,frames=adapter.animation_manifest})
end
local function image(animation,i)
  local path=animation.raster.prefix..((animation.raster.stage-1)*animation.steps+i)..'.png'
  path=path:gsub('\\','/')
  assert(not path:find('[%%{}\r\n]'),'unsupported TeX characters in animation cache path')
  return string.format('\\pgftext[left,bottom,at=\\pgfpointorigin]{\\includegraphics[width=%.8fpt,height=%.8fpt]{\\detokenize{%s}}}',
    animation.spec.width,animation.spec.height,path)
end
function C.typeset(animation,i)
  local pt=require('flora.paint').new({backend='pgf'})
  pt:emit(image(animation,i))
  flora.typeset_page(pt,animation.spec,animation.args)
end
-- The interval's start sample as a static image, and over it either one
-- Movie annotation that plays the external GIF once, or a Screen annotation
-- with the GIF embedded in the PDF. The page is covered either way.
function C.typeset_gif(animation)
  local raster=animation.raster
  local pt=require('flora.paint').new({backend='pgf'})
  pt:emit(image(animation,0))
  if raster.embed then
    local path=assert(raster.gif,'missing GIF playback file'):gsub('\\','/')
    assert(not path:find('[%%{}#^\r\n]'),'unsupported TeX characters in GIF playback path')
    local name=path:match('[^/]+$')
    assert(not name:find('[()]'),'unsupported characters in GIF file name; rename the document')
    if kpse and kpse.record_input_file then kpse.record_input_file(path) end
    -- The physical page is the one being shipped: total_pages counts finished ones.
    pt:emit(string.format('\\pgftext[left,bottom,at=\\pgfpointorigin]{\\floralembedgif{\\detokenize{%s}}{\\detokenize{%s}}{%.8fpt}{%.8fpt}{%d}}',
      path,name,animation.spec.width,animation.spec.height,(status and status.total_pages or 0)+1))
  else
    local path=assert(raster.gif_relative,'missing GIF playback file')
    assert(not path:find('[()\\%%{}#^\r\n]'),
      'unsupported characters in GIF playback path; rename the document or its output directory')
    pt:emit(string.format('\\pgftext[left,bottom,at=\\pgfpointorigin]{\\pdfextension annot width %.8fpt height %.8fpt depth 0pt{'
      ..'/Subtype /Movie /Border [0 0 0] /T (floral-%d-%d) /Movie << /F (\\detokenize{%s}) >> '
      ..'/A << /Mode /Once /ShowControls false >>}}',
      animation.spec.width,animation.spec.height,animation.count,raster.stage,path))
  end
  flora.typeset_page(pt,animation.spec,animation.args)
end
return C
