-- Box diagnostics are regressions in this focused fixture, even if TeX succeeds.
local path=assert(arg[1], 'pass a TeX log path')
local file=assert(io.open(path))
local log=file:read('*a'); file:close()
assert(not log:match('Overfull \\[hv]box'), 'Overfull box in '..arg[1])
assert(not log:match('Underfull \\[hv]box'), 'Underfull box in '..arg[1])
print('No box diagnostics: '..arg[1])
