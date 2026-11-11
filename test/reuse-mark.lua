-- Loaded by test/reuse-mark.tex: logs, for test/check_reuse_mark.lua, each
-- header-slot ornament painted (its kind and page box, then the box
-- widened by the kind's reach, all it may paint), each running-head rule,
-- and each frame's reserved boxes. Lines stay short of TeX's 79-column
-- wrap.
local Orn=require('flora.ornaments')
local Paint=require('flora.paint')
local P=getmetatable(Paint.new({})).__index
local function frame() return beamer_floral.count end
local draw=Orn.draw
Orn.draw=function(kind,pt,rng,box,o)
  local k=type(kind)=='string' and Orn.kinds[kind] or kind
  if k and k.slot=='header' then
    local pj=pt:_pj()
    local x0,y0,x1,y1=box[1],box[2],box[3],box[4]
    if pj then x0,y0=pj(x0,y0); x1,y1=pj(x1,y1) end
    x0,x1=math.min(x0,x1),math.max(x0,x1)
    y0,y1=math.min(y0,y1),math.max(y0,y1)
    texio.write_nl('log',string.format('bf test: frame %d stage %d mark %s %.3f %.3f %.3f %.3f',
      frame(),beamer_floral.stage,k.name,x0,y0,x1,y1))
    local r=(k.reach or 0)*(x1-x0)
    texio.write_nl('log',string.format('bf ink: frame %d %.3f %.3f %.3f %.3f',frame(),x0-r,y0-r,x1+r,y1+r))
  end
  return draw(kind,pt,rng,box,o)
end
-- The rule: a two-point horizontal stroke 0.4 pt wide at opacity 0.9.
local stroke=P.stroke
P.stroke=function(pt,cmds,rgb,w,a,...)
  if w==0.4 and a==0.9 and #cmds==2 and cmds[1][1]=='m' and cmds[2][1]=='l' then
    local pj=pt:_pj()
    local x0,y0,x1,y1=cmds[1][2],cmds[1][3],cmds[2][2],cmds[2][3]
    if pj then x0,y0=pj(x0,y0); x1,y1=pj(x1,y1) end
    if math.abs(y0-y1)<1e-9 then
      texio.write_nl('log',string.format('bf rule: frame %d %.3f %.3f %.3f',frame(),math.min(x0,x1),math.max(x0,x1),y0))
    end
  end
  return stroke(pt,cmds,rgb,w,a,...)
end
local prepare=beamer_floral.prepare
beamer_floral.prepare=function(spec)
  for _,r in ipairs(spec.reserve or {}) do
    texio.write_nl('log',string.format('bf reserve: frame %d %.3f %.3f %.3f %.3f',beamer_floral.count,r[1],r[2],r[3],r[4]))
  end
  return prepare(spec)
end
