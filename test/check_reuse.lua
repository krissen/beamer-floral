-- Usage: texlua test/check_reuse.lua reuse.log
local f=assert(io.open(arg[1],'r')); local log=f:read('a'); f:close()
-- content: one-line titled, untitled, two-line titled, reserved strip.
local want={title=1,section=1,content=4}
local failed=false
for class,n in pairs(want) do
  local _,got=log:gsub('drew reused flora for class '..class,'')
  if got~=n then print(('FAIL %s: %d drawings, expected %d'):format(class,got,n)); failed=true end
end
if failed then os.exit(1) end
print('PASS reused drawings')
