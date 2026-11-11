-- Usage: texlua test/check_reuse_mark.lua reuse-mark.log reuse-mark-adaptive.log [reuse-stock.log]
-- Reused pages carry their own running-head mark. For each frame of
-- test/reuse-mark.tex, the marks every reused page logs ("reused page
-- marks") must match, in size and height, the marks the adaptive build
-- paints for the same frame; every overlay of a frame logs the same marks;
-- the pages of one class show one kind; and no mark is under the 10 pt
-- minimum. A stock-theme log, when given, must show reused pages without a
-- mark, as stock themes have none.
local function read(path)
  local f=assert(io.open(path,'r')); local text=f:read('a'); f:close()
  -- TeX wraps log lines at about 79 characters. The lines read here are
  -- written shorter, so what TeX appends to them (an image's file name)
  -- may wrap but never splits their own text.
  local out={}
  for line in (text..'\n'):gmatch('([^\n]*)\n') do out[#out+1]=line end
  return out
end
local failed=false
local function fail(...) print(string.format(...)); failed=true end

-- {frame -> list of "size y"} from the adapter's reused-page lines, and the
-- number of pages each frame logged.
local function reused_marks(lines)
  local marks,pages={},{}
  local function close(n)
    local m=marks[n]
    if not m or not m.open then return end
    m.open=false
    if #m.page~=m.count then fail('FAIL frame %d: %d marks counted, %d listed',n,m.count,#m.page) end
    table.sort(m.page,function(a,b) return a[2]<b[2] or a[2]==b[2] and a[1]<b[1] end)
    local key={}
    for _,x in ipairs(m.page) do key[#key+1]=string.format('%.2f/%.2f',x[1],x[2]) end
    key=table.concat(key,' ')
    if m.key and m.key~=key then fail('FAIL frame %d: its pages log different marks (%s, %s)',n,m.key,key) end
    m.key,m.list=key,m.page
  end
  local last
  for _,line in ipairs(lines) do
    local n,count=line:match('beamer%-floral: frame (%d+) reused page marks (%d+)')
    if n then
      if last then close(last) end
      n=tonumber(n); last=n
      marks[n]=marks[n] or {}
      marks[n].open,marks[n].count,marks[n].page=true,tonumber(count),{}
      pages[n]=(pages[n] or 0)+1
    else
      local k,size,y=line:match('beamer%-floral: frame (%d+) reused page mark ([%d.]+) pt at ([%d.]+)')
      if k then
        k=tonumber(k)
        if k~=last then fail('FAIL frame %d: a mark logged outside its page',k)
        else table.insert(marks[k].page,{tonumber(size),tonumber(y)}) end
      end
    end
  end
  if last then close(last) end
  return marks,pages
end
-- {frame -> list of {size, y, kind, x0}} from the test document's hook.
local function painted_marks(lines)
  local marks={}
  for _,line in ipairs(lines) do
    local n,kind,x0,y0,x1,y1=line:match('bf test: frame (%d+) stage %d+ mark (%a+) +([%d.-]+) +([%d.-]+) +([%d.-]+) +([%d.-]+)')
    if n then
      n=tonumber(n); x0,y0,x1,y1=tonumber(x0),tonumber(y0),tonumber(x1),tonumber(y1)
      marks[n]=marks[n] or {}
      local list=marks[n]
      local m={x1-x0,(y0+y1)/2,kind,x0}
      local seen=false
      for _,o in ipairs(list) do
        if math.abs(o[1]-m[1])<2e-3 and math.abs(o[2]-m[2])<2e-3 and math.abs(o[4]-m[4])<2e-3 then seen=true end
      end
      if not seen then list[#list+1]=m end
    end
  end
  for _,list in pairs(marks) do
    table.sort(list,function(a,b) return a[2]<b[2] or a[2]==b[2] and a[1]<b[1] end)
  end
  return marks
end
local function classes(lines)
  local out={}
  for _,line in ipairs(lines) do
    local n,class,decision=line:match('beamer%-floral: frame (%d+) class (%a+) reuse (%a+)')
    if n then out[tonumber(n)]={class=class,reused=decision=='yes'} end
  end
  return out
end

local reuse_log,adaptive_log,stock_log=arg[1],arg[2],arg[3]
if not (reuse_log and adaptive_log) then
  print('usage: texlua test/check_reuse_mark.lua reuse-mark.log reuse-mark-adaptive.log [reuse-stock.log]')
  os.exit(2)
end
local reuse_lines,adaptive_lines=read(reuse_log),read(adaptive_log)
local reused,pages=reused_marks(reuse_lines)
local adaptive=painted_marks(adaptive_lines)
local class=classes(reuse_lines)
local frames=0
for n in pairs(class) do frames=math.max(frames,n) end
if frames<13 then fail('FAIL %s: %d frames, expected 13',reuse_log,frames) end
for n=1,frames do
  if not class[n].reused then fail('FAIL frame %d: not reused',n) end
  local r=reused[n] and reused[n].list
  local a=adaptive[n] or {}
  if not r then fail('FAIL frame %d: no reused-page marks logged',n)
  elseif #r~=#a then fail('FAIL frame %d: %d marks reused, %d adaptive',n,#r,#a)
  else
    for i,m in ipairs(r) do
      if math.abs(m[1]-a[i][1])>0.011 or math.abs(m[2]-a[i][2])>0.011 then
        fail('FAIL frame %d mark %d: reused %.2f pt at %.2f, adaptive %.2f pt at %.2f',n,i,m[1],m[2],a[i][1],a[i][2])
      end
      if m[1]<10-1e-6 then fail('FAIL frame %d: a %.2f pt mark is under the minimum',n,m[1]) end
    end
  end
end
-- Overlays: the paused frame logs three pages, the frame with \only two.
if pages[7]~=3 or pages[8]~=2 then fail('FAIL overlays: frame 7 logged %s pages, frame 8 %s',pages[7],pages[8]) end
-- One kind per class: the marks of the left margin, as painted under reuse.
local painted=painted_marks(reuse_lines)
local kinds={}
for n,list in pairs(painted) do
  for _,m in ipairs(list) do
    if m[4]<200 then
      local c=class[n] and class[n].class or '?'
      kinds[c]=kinds[c] or {}
      kinds[c][m[3]]=true
    end
  end
end
for c,set in pairs(kinds) do
  local names={}
  for k in pairs(set) do names[#names+1]=k end
  if #names~=1 then table.sort(names); fail('FAIL class %s: kinds %s, expected one',c,table.concat(names,', ')) end
end
if stock_log then
  local stock=reused_marks(read(stock_log))
  local any=false
  for n,m in pairs(stock) do
    any=true
    if #m.list>0 then fail('FAIL %s frame %d: a stock theme page shows a mark',stock_log,n) end
  end
  if not any then fail('FAIL %s: no reused page logged its marks',stock_log) end
end
if failed then os.exit(1) end
print('PASS reused pages carry their own marks')
