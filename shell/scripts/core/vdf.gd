## Valve KeyValues readers: text VDF/ACF (libraryfolders.vdf, appmanifest_*.acf,
## localconfig.vdf, loginusers.vdf) and binary VDF (userdata/*/config/shortcuts.vdf;
## appcache/appinfo.vdf has its own streaming reader, SteamAppInfo).
## Pure functions, no I/O beyond reading the given bytes, so they are unit-tested
## headless against fixtures.
class_name Vdf
extends RefCounted


## Parses text KeyValues. Keys keep their original case; use get_ci() to look up
## case-insensitively (Steam writes "apps" and "Apps" in different files/versions).
static func parse_text(text: String) -> Dictionary:
	var tokens := _tokenize(text)
	var pos := [0]
	return _parse_block(tokens, pos)


static func _tokenize(text: String) -> PackedStringArray:
	# Token kinds: "{" , "}" , or a string prefixed with "s". Scans with find()/substr()
	# rather than per-character Strings: localconfig.vdf of a large account is several MB
	# and is read while the shell starts.
	var out := PackedStringArray()
	var i := 0
	var n := text.length()
	var bs := text.find("\\")  # next backslash; re-searched only once passed (no O(n²))
	while i < n:
		var c := text.unicode_at(i)
		if c == 32 or c == 9 or c == 10 or c == 13:
			i += 1
		elif c == 47 and i + 1 < n and text.unicode_at(i + 1) == 47:  # // comment
			var e := text.find("\n", i)
			i = n if e < 0 else e
		elif c == 123:
			out.append("{")
			i += 1
		elif c == 125:
			out.append("}")
			i += 1
		elif c == 34:  # quoted string with \n \t \\ \" escapes
			var p := i + 1
			var buf := ""
			while true:
				var q := text.find("\"", p)
				if q < 0:
					q = n
				if bs >= 0 and bs < p:
					bs = text.find("\\", p)
				var b := bs
				if b >= 0 and b < q and b + 1 < n:
					buf += text.substr(p, b - p)
					var e := text[b + 1]
					match e:
						"n": buf += "\n"
						"t": buf += "\t"
						"\\": buf += "\\"
						"\"": buf += "\""
						_: buf += "\\" + e
					p = b + 2
					continue
				buf += text.substr(p, q - p)
				i = q + 1
				break
			out.append("s" + buf)
		elif c == 91:
			# Conditional like [$WIN32]: ignored, as Steam does on Linux for these files.
			var e2 := text.find("]", i)
			i = n if e2 < 0 else e2 + 1
		else:
			var start := i
			while i < n:
				var d := text.unicode_at(i)
				if d == 32 or d == 9 or d == 10 or d == 13 or d == 123 or d == 125 or d == 34:
					break
				i += 1
			out.append("s" + text.substr(start, i - start))
	return out


static func _parse_block(tokens: PackedStringArray, pos: Array) -> Dictionary:
	var result := {}
	while pos[0] < tokens.size():
		var t: String = tokens[pos[0]]
		if t == "}":
			pos[0] += 1
			return result
		if t == "{":  # stray brace: skip
			pos[0] += 1
			continue
		var key := t.substr(1)
		pos[0] += 1
		if pos[0] >= tokens.size():
			break
		var v: String = tokens[pos[0]]
		if v == "{":
			pos[0] += 1
			result[key] = _parse_block(tokens, pos)
		elif v == "}":
			result[key] = ""
		else:
			result[key] = v.substr(1)
			pos[0] += 1
	return result


## Case-insensitive child lookup.
static func get_ci(d: Variant, key: String, default: Variant = null) -> Variant:
	if not (d is Dictionary):
		return default
	if d.has(key):
		return d[key]
	var lk := key.to_lower()
	for k in d.keys():
		if str(k).to_lower() == lk:
			return d[k]
	return default


## Walks a path of keys case-insensitively: get_path_ci(d, ["UserLocalConfigStore", "Software", ...]).
static func get_path_ci(d: Variant, path: Array, default: Variant = null) -> Variant:
	var cur: Variant = d
	for k in path:
		cur = get_ci(cur, str(k))
		if cur == null:
			return default
	return cur


# --- binary KeyValues ------------------------------------------------------
const _BIN_MAP := 0x00
const _BIN_STRING := 0x01
const _BIN_INT32 := 0x02
const _BIN_FLOAT32 := 0x03
const _BIN_POINTER := 0x04
const _BIN_WSTRING := 0x05
const _BIN_COLOR := 0x06
const _BIN_UINT64 := 0x07
const _BIN_END := 0x08
const _BIN_INT64 := 0x0A
const _BIN_END_ALT := 0x0B


## Parses binary KeyValues as used by shortcuts.vdf. Never raises: on malformed or
## truncated data the map being read when the data broke is dropped and everything
## complete before it is kept (a shortcuts.vdf cut short loses its last entry, not all).
static func parse_binary(data: PackedByteArray) -> Dictionary:
	var pos := [0, false]
	var r: Variant = _bin_map(data, pos)
	return r if r is Dictionary else {}


static func _bin_cstr(data: PackedByteArray, pos: Array) -> Variant:
	var start: int = pos[0]
	var end := data.find(0, start)
	if end < 0:
		return null
	pos[0] = end + 1
	return data.slice(start, end).get_string_from_utf8()


## Returns the map, or null when the data broke inside this map itself (the caller drops
## it). When a nested map broke, returns what was complete with pos[1] = true.
static func _bin_map(data: PackedByteArray, pos: Array) -> Variant:
	var result := {}
	while pos[0] < data.size():
		var t: int = data[pos[0]]
		pos[0] += 1
		if t == _BIN_END or t == _BIN_END_ALT:
			return result
		var key: Variant = _bin_cstr(data, pos)
		if key == null:
			return null
		match t:
			_BIN_MAP:
				var child: Variant = _bin_map(data, pos)
				if child != null:
					result[key] = child
				if child == null or pos[1]:
					pos[1] = true
					return result
			_BIN_STRING:
				var s: Variant = _bin_cstr(data, pos)
				if s == null:
					return null
				result[key] = s
			_BIN_INT32, _BIN_FLOAT32, _BIN_POINTER, _BIN_COLOR:
				if pos[0] + 4 > data.size():
					return null
				if t == _BIN_FLOAT32:
					result[key] = data.decode_float(pos[0])
				else:
					result[key] = data.decode_s32(pos[0])
				pos[0] += 4
			_BIN_UINT64, _BIN_INT64:
				if pos[0] + 8 > data.size():
					return null
				result[key] = data.decode_s64(pos[0])
				pos[0] += 8
			_BIN_WSTRING:  # UTF-16LE, ends with a 2-byte zero
				var p: int = pos[0]
				while p + 1 < data.size() and (data[p] != 0 or data[p + 1] != 0):
					p += 2
				if p + 1 >= data.size():
					return null
				result[key] = data.slice(pos[0], p).get_string_from_utf16()
				pos[0] = p + 2
			_:
				return null
	# Top level of shortcuts.vdf ends with two END bytes; running out at top level is fine.
	return result
