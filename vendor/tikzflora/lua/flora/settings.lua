-- Document settings from \florasetup and \florathispage: a key=value list,
-- parsed and checked here so mistakes are reported with the key's name.
--
--   layout    left, right, centered, split, title or surround (frames.lua)
--   seed      a number, or random
--   mix       weights per kind of growth, e.g. mix={lily=2, umbel=0}
--             (mix.lua lists the kinds)
--   density   how full the border grows (mix.density); below 1 is airier
--   visitors  the weight of every visitor at once (bee, butterfly, bird,
--             snail); mix={bee=0} after it still turns one off
--   palette   what paints each part, e.g. palette={leaves=green,
--             hero=kon-peki}: look, an ink group, one ink (inks.lua), or
--             random for one ink picked per page
--   spin      a number that re-picks the random inks; the shapes stay
--   ornaments weights per ornament kind, e.g. ornaments={moon=2, night=0}
--             (ornaments.lua registers the kinds; each slot picks one)

local M = {}

local Frames = require("flora.frames")
local Tune = require("flora.tune")
local Inks = require("flora.inks")
local Mix = require("flora.mix")
local Orn = require("flora.ornaments")

-- Key name -> function(value string) returning the parsed value, or nil
-- and a message.
local keys = {}

function M.define(name, parse)
  keys[name] = parse
end

M.define("layout", function(v)
  if Frames.layouts[v] then return v end
  return nil, "layout must be one of left, right, centered, split, title, surround"
end)

M.define("seed", function(v)
  if v == "random" or tonumber(v) then return v end
  return nil, "seed must be a number or random"
end)

local function weight(v)
  local n = tonumber(v)
  if n and n >= 0 and n <= 10 then return n end
end

local function known(t)
  local out = {}
  for k in pairs(t) do out[#out + 1] = k end
  table.sort(out)
  return table.concat(out, ", ")
end

local function is_list(t)
  return type(t) == "table" and #t > 0
end

M.define("density", function(v)
  local n = weight(v)
  if n then return n end
  return nil, "density must be a number from 0 to 10"
end)

-- A shorthand for every visitor's weight.
M.define("visitors", function(v)
  local n = weight(v)
  if n then return n end
  return nil, "visitors must be a number from 0 to 10"
end)

M.define("mix", function(v)
  local t = {}
  for _, kv in ipairs(M.parse_list(v)) do
    local k, w = kv[1], weight(kv[2])
    if Tune.mix[k] == nil then return nil, "no kind \"" .. k .. "\" (kinds: " .. known(Tune.mix) .. ")" end
    if not w then return nil, k .. " needs a weight from 0 to 10" end
    t[k] = w
  end
  return t
end)

M.define("ornaments", function(v)
  local t = {}
  for _, kv in ipairs(M.parse_list(v)) do
    local k, w = kv[1], weight(kv[2])
    if not Orn.kinds[k] then return nil, "no ornament \"" .. k .. "\" (kinds: " .. known(Orn.kinds) .. ")" end
    if not w then return nil, k .. " needs a weight from 0 to 10" end
    t[k] = w
  end
  return t
end)

M.define("palette", function(v)
  local t = {}
  for _, kv in ipairs(M.parse_list(v)) do
    local part, ink = kv[1], kv[2]
    if Tune.color.palette[part] == nil then
      return nil, "no part \"" .. part .. "\" (parts: " .. known(Tune.color.palette) .. ")"
    end
    if not (ink == "look" or ink == "random" or Inks.groups[ink] or Inks.ramps[ink]) then
      return nil, "\"" .. tostring(ink) .. "\" is not look, random, an ink group or an ink name"
    end
    t[part] = ink
  end
  return t
end)

M.define("spin", function(v)
  local n = tonumber(v)
  if n and n == math.floor(n) and n >= 0 then return n end
  return nil, "spin must be a whole number"
end)

local function trim(s)
  return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end

-- Split "a=1, b={x=2, y=3}" at top-level commas into {name, value} pairs;
-- braces around a value are removed. A key without "=" has value nil.
function M.parse_list(s)
  local out, depth, start = {}, 0, 1
  local function take(piece)
    piece = trim(piece)
    if piece == "" then return end
    local k, v = piece:match("^([^=]-)%s*=%s*(.*)$")
    if not k then
      out[#out + 1] = { trim(piece), nil }
      return
    end
    v = trim(v)
    local inner = v:match("^{(.*)}$")
    out[#out + 1] = { trim(k), inner and trim(inner) or v }
  end
  for i = 1, #s do
    local ch = s:sub(i, i)
    if ch == "{" then depth = depth + 1
    elseif ch == "}" then depth = depth - 1
      if depth < 0 then error("unbalanced braces in \"" .. s .. "\"") end
    elseif ch == "," and depth == 0 then
      take(s:sub(start, i - 1))
      start = i + 1
    end
  end
  if depth ~= 0 then error("unbalanced braces in \"" .. s .. "\"") end
  take(s:sub(start))
  return out
end

-- Tune overrides for the engine: a table of settings mirroring tune.lua's
-- T, e.g. tune={compose={hero=0.3}, plant={root=0.72}}. Dotted names
-- (compose.hero=0.3) are accepted too. Every path is checked against the
-- tuner's own index (tune.lua's _doc), so a typo names the key and lists
-- what may be set there.
local parse_tune_table

local function split_fields(s)
  local out, depth, start = {}, 0, 1
  for i = 1, #s do
    local ch = s:sub(i, i)
    if ch == "{" then depth = depth + 1
    elseif ch == "}" then depth = depth - 1
      if depth < 0 then error("unbalanced braces in \"" .. s .. "\"", 0) end
    elseif ch == "," and depth == 0 then
      local piece = trim(s:sub(start, i - 1))
      if piece ~= "" then out[#out + 1] = piece end
      start = i + 1
    end
  end
  if depth ~= 0 then error("unbalanced braces in \"" .. s .. "\"", 0) end
  local piece = trim(s:sub(start))
  if piece ~= "" then out[#out + 1] = piece end
  return out
end

local function parse_tune_value(v)
  v = trim(v)
  local inner = v:match("^{(.*)}$")
  if inner then return parse_tune_table(inner) end
  local n = tonumber(v)
  if n then return n end
  if v == "" then error("empty tune value", 0) end
  return v
end

-- Assign a.b.c like a={b={c=...}} in `map`.
local function nest(map, name, value)
  local parts = {}
  for part in name:gmatch("[^.]+") do parts[#parts + 1] = part end
  local t = map
  for i = 1, #parts - 1 do
    local k = parts[i]
    if type(t[k]) ~= "table" then t[k] = {} end
    t = t[k]
  end
  t[parts[#parts]] = value
end

parse_tune_table = function(s)
  local fields = split_fields(s)
  local list, map = {}, {}
  local has_list, has_map = false, false
  for _, f in ipairs(fields) do
    local k, v = f:match("^([^=]-)%s*=%s*(.*)$")
    if k then
      has_map = true
      nest(map, trim(k), parse_tune_value(v))
    else
      has_list = true
      list[#list + 1] = parse_tune_value(f)
    end
  end
  if has_list and has_map then
    error("a tune table mixes a list and named keys", 0)
  end
  return has_list and list or map
end

local function tune_names(t)
  local out = {}
  for k in pairs(t) do
    if type(k) == "string" and k:sub(1, 1) ~= "_" then out[#out + 1] = k end
  end
  table.sort(out)
  return table.concat(out, ", ")
end

local function validate_tune(over, base, path)
  if is_list(over) then
    if not is_list(base) then
      error(string.format("%s: expected named settings, got a list", path:gsub("%.$", "")), 0)
    end
    if #over ~= #base then
      error(string.format("%s: expected %d values, got %d", path:gsub("%.$", ""), #base, #over), 0)
    end
    for i, v in ipairs(over) do
      local p = path:gsub("%.$", "") .. "[" .. i .. "]"
      local b = base[i]
      if type(b) == "table" then
        if type(v) ~= "table" then error(p .. ": expected a list or table", 0) end
        validate_tune(v, b, p .. ".")
      elseif type(v) ~= type(b) then
        error(string.format("%s: expected %s, got %s", p, type(b), type(v)), 0)
      end
    end
    return
  end
  for k, v in pairs(over) do
    if type(k) ~= "string" or k:sub(1, 1) == "_" then
      error(string.format("%s: \"%s\" is not a tune setting", path:gsub("%.$", ""), tostring(k)), 0)
    end
    local b = base[k]
    if b == nil then
      error(string.format("%s: no tune key \"%s\" (keys here: %s)",
        path:gsub("%.$", ""), path .. k, tune_names(base)), 0)
    end
    local p = path .. k
    if type(b) == "table" then
      if type(v) ~= "table" then
        error(string.format("%s: expected a list or table", p), 0)
      end
      validate_tune(v, b, p .. ".")
    elseif type(v) ~= type(b) then
      error(string.format("%s: expected %s, got %s", p, type(b), type(v)), 0)
    end
  end
end

M.define("tune", function(v)
  local ok, t = pcall(parse_tune_table, v)
  if not ok then return nil, tostring(t) end
  local valid, msg = pcall(validate_tune, t, Tune, "tune.")
  if not valid then return nil, tostring(msg) end
  return t
end)

-- Parse a key=value list into a settings table. Errors name the key.
function M.parse(s)
  local t = {}
  for _, kv in ipairs(M.parse_list(s)) do
    local k, v = kv[1], kv[2]
    local parse = keys[k]
    if not parse then
      local known = {}
      for name in pairs(keys) do known[#known + 1] = name end
      table.sort(known)
      error(string.format("unknown key \"%s\" (known keys: %s)", k, table.concat(known, ", ")))
    end
    if v == nil then error(string.format("key \"%s\" needs a value", k)) end
    local val, msg = parse(v)
    if val == nil then error(string.format("%s: %s (got \"%s\")", k, msg, v)) end
    if k == "density" then
      t.mix = M.merge({ mix = t.mix }, { mix = { density = val } }).mix
    elseif k == "visitors" then
      local m = {}
      for _, name in ipairs(Mix.visitors) do m[name] = val end
      t.mix = M.merge({ mix = t.mix }, { mix = m }).mix
    else
      t[k] = M.merge({ [k] = t[k] }, { [k] = val })[k]
    end
  end
  return t
end

-- Merge settings table `over` onto `base`, returning a new table. Named
-- tables (such as mix, palette and tune) merge key by key at every depth,
-- so a later \florasetup can adjust one engine value without repeating the
-- rest. Lists (ranges, control points) are replaced whole.
local function merge_into(base, over)
  local t = {}
  for k, v in pairs(base) do t[k] = v end
  for k, v in pairs(over) do
    if type(v) == "table" and type(t[k]) == "table"
      and not is_list(v) and not is_list(t[k]) then
      t[k] = merge_into(t[k], v)
    else
      t[k] = v
    end
  end
  return t
end

function M.merge(base, over)
  return merge_into(base or {}, over or {})
end

return M
