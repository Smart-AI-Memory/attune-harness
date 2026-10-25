#!lua name=attune_harness_memory_v1

-- Only the derived native generation prefix supplied by the host is accepted.
local function prefix_for(args)
  local prefix = args[1]
  if type(prefix) ~= 'string' or #prefix > 128 or
     not string.match(prefix, '^attune:harness:hydration:[%w_-]+:[a-f0-9]+:$') then
    error('invalid hydration generation prefix')
  end
  return prefix
end

local function digest(keys, args)
  local prefix = prefix_for(args)
  local limit = tonumber(args[2]) or 5
  if limit < 1 or limit > 100 or limit ~= math.floor(limit) then error('invalid digest limit') end
  local context = redis.call('GET', prefix .. 'context') or ''
  local terms = {}
  for term in string.gmatch(context, '%S+') do table.insert(terms, term) end
  local rows = {}
  for _, id in ipairs(redis.call('SMEMBERS', prefix .. 'status:active')) do
    local f = redis.call('HMGET', prefix .. 'node:' .. id,
                        'type', 'name', 'description', 'updated_at', 'tags')
    if not f[2] then error('incomplete curated record') end
    local hay = string.lower((f[2] or '') .. ' ' .. (f[3] or '') .. ' ' .. (f[5] or ''))
    local score = 0
    for _, term in ipairs(terms) do
      if string.find(hay, term, 1, true) then score = score + 1 end
    end
    table.insert(rows, {id=id, type=f[1], name=f[2], description=f[3], updated_at=f[4], score=score})
  end
  table.sort(rows, function(a, b)
    if a.score ~= b.score then return a.score > b.score end
    if (a.updated_at or '') ~= (b.updated_at or '') then return (a.updated_at or '') > (b.updated_at or '') end
    return a.id < b.id
  end)
  local out = {}
  for i = 1, math.min(limit, #rows) do
    rows[i].edges = redis.call('LRANGE', prefix .. 'edges:' .. rows[i].id, 0, -1)
    table.insert(out, cjson.encode(rows[i]))
  end
  return out
end

local function pointer(prefix, id)
  local suffix = string.sub(id, 1, 5) == 'file:' and id or 'node:' .. id
  local f = redis.call('HMGET', prefix .. suffix, 'name', 'description', 'path', 'layer', 'type')
  if not f[1] then return nil end
  return {id=id, name=f[1], description=f[2], path=f[3], layer=f[4], type=f[5]}
end

local function related(keys, args)
  local prefix, id = prefix_for(args), args[2]
  if type(id) ~= 'string' or #id > 128 or not string.match(id, '^[%w_.:%-]+$') then
    error('invalid memory id')
  end
  local self = pointer(prefix, id)
  if not self then return {} end
  local out = {cjson.encode(self)}
  for _, raw in ipairs(redis.call('LRANGE', prefix .. 'edges:' .. id, 0, -1)) do
    local edge = cjson.decode(raw)
    local neighbor = pointer(prefix, edge.target)
    if neighbor then
      neighbor.edge_type = edge.type
      table.insert(out, cjson.encode(neighbor))
    end
  end
  return out
end

redis.register_function{function_name='harness_recall_digest_v1', callback=digest, flags={'no-writes'}}
redis.register_function{function_name='harness_recall_related_v1', callback=related, flags={'no-writes'}}
