-- Usage: texlua test/check_reuse.lua reuse.log [reuse-stock.log ...]
-- Compares each frame's logged reuse decision with the expected table for
-- that document, and counts the reused drawings per class.
local expected={
  reuse={
    decisions={
      'title yes', 'section yes', 'content yes', 'content yes', 'content yes',
      'section yes', 'content yes', 'content yes',
      'content no (not listed)',  -- \florathisframe{reuse=none}
      'content no (growing)',     -- growth=overlays
      'content yes', 'content yes',
      'content no (not listed)',  -- \florathisframe{reuse=title}
      'content yes',              -- the document setting again
      'section yes',              -- after \florasetup{reuse={title,section}}
      'content no (not listed)',
      'content no (not listed)',  -- after \florasetup{reuse=none}
    },
    -- content: one-line titled, untitled, two-line titled, reserved strip.
    drawings={title=1, section=1, content=4},
  },
  -- Patterns keep their own drawings under reuse: a reused drawing keeps the
  -- text block clear and leaves a pattern nothing to fill. The frame with
  -- pattern=none is flora and is reused.
  patterns={
    decisions={'content no (pattern)', 'content no (pattern)', 'content yes',
      'content no (pattern)', 'content no (growing)'},
    drawings={title=0, section=0, content=1},
  },
  ['reuse-stock']={
    decisions={'title yes', 'section no (not listed)', 'content no (not listed)'},
    drawings={title=1, section=0, content=0},
  },
}
local failed=false
local function fail(...) print(string.format(...)); failed=true end
for _,path in ipairs(arg) do
  local job=path:match('([^/\\]+)%.log$')
  local want=expected[job]
  if not want then fail('FAIL %s: no expected table', path) else
    local f=assert(io.open(path,'r')); local log=f:read('a'); f:close()
    local got={}
    for n,class,decision in log:gmatch('beamer%-floral: frame (%d+) class (%a+) reuse (%a+[%a ()]*)') do
      got[tonumber(n)]=class..' '..decision:gsub('%s+$','')
    end
    for n=1,math.max(#want.decisions,#got) do
      if got[n]~=want.decisions[n] then
        fail('FAIL %s frame %d: %s, expected %s', job, n, tostring(got[n]), tostring(want.decisions[n]))
      end
    end
    for class,count in pairs(want.drawings) do
      local _,drawn=log:gsub('drew reused flora for class '..class..'[^\n]*','')
      if drawn~=count then fail('FAIL %s %s: %d drawings, expected %d', job, class, drawn, count) end
    end
  end
end
if failed then os.exit(1) end
print('PASS reuse decisions and drawings')
