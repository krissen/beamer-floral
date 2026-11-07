-- Merge document startup without replacing links or unrelated JavaScript.
local C=dofile('beamer-floral-pdf.lua')
local reference='99 0 R'
local names='/EmbeddedFiles 3 0 R /JavaScript << /Names [(aaa) 7 0 R (zzz) 8 0 R] >>'
local merged=C._merge_names(names,reference)
assert(merged:find('/EmbeddedFiles 3 0 R',1,true),'other name trees must survive')
assert(merged:find('(aaa) 7 0 R (beamer-floral-growth) 99 0 R (zzz) 8 0 R',1,true),
  'JavaScript names must remain sorted and preserve existing actions')
local hex=C._merge_names('/JavaScript << /Names [<61> 1 0 R <7a> 2 0 R] /Limits [<61> <7a>] >>',reference)
assert(hex:find('/Limits [<61> <7a>]',1,true),'existing name-tree limits must be retained')
assert(not pcall(C._merge_names,'/JavaScript 7 0 R',reference),'indirect trees must not be overwritten')
local output,objects='',{}
pdf={getnames=function()return '/EmbeddedFiles 3 0 R' end,
 setnames=function(s)output=s end,
 immediateobj=function(a,b)objects[#objects+1]=b or a;return #objects end}
C.note(3);C.note(1);C.note(3);C.finish()
assert(output:find('/EmbeddedFiles 3 0 R',1,true))
assert(output:find('/JavaScript',1,true))
assert(objects[1]:find('function floralPrepare',1,true),'startup preparation missing')
assert(objects[1]:find('"1":true,"3":true',1,true),'only owned animation IDs may be prepared')
print('PDF document-startup merge tests passed')
