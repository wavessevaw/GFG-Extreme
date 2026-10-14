## Valve KeyValues readers: text VDF/ACF (libraryfolders.vdf, appmanifest_*.acf,
## localconfig.vdf, loginusers.vdf) and binary VDF (userdata/*/config/shortcuts.vdf).
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
	# Token kinds: "{" , "}" , or a string prefixed with "s".
	var out := PackedStringArray()
	var i := 0
	var n := text.length()
	while i < n:
		var c := text[i]
		if c == " " or c == "\t" or c == "\n" or c == "\r":
			i += 1
		elif c == "/" and i + 1 < n and text[i + 1] == "/":
			while i < n and text[i] != "\n":
				i += 1
		elif c == "{" or c == "}":
			out.append(c)
			i += 1
		elif c == "\"":
			i += 1
			var buf := ""
			while i < n and text[i] != "\"":
				if text[i] == "\\" and i + 1 < n:
					var e := text[i + 1]
					match e:
						"n": buf += "\n"
						"t": buf += "\t"
						"\\": buf += "\\"
						"\"": buf += "\""
						_: buf += "\\" + e
					i += 2
				else:
					buf += text[i]
					i += 1
			i += 1
			out.append("s" + buf)
		elif c == "[":
			# Conditional like [$WIN32]: ignored, as Steam does on Linux for these files.
			while i < n and text[i] != "]":
				i += 1
			i += 1
		else:
			var start := i
			while i < n and not (text[i] in [" ", "\t", "\n", "\r", "{", "}", "\""]):
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
const _BIN_UINT64 := 0x07
const _BIN_END := 0x08
const _BIN_INT64 := 0x0A


## Parses binary KeyValues as used by shortcuts.vdf. Returns {} on malformed data
## rather than raising: a corrupt file must never take the shell down.
static func parse_binary(data: PackedByteArray) -> Dictionary:
	var pos := [0]
	var r: Variant = _bin_map(data, pos)
	return r if r is Dictionary else {}


static func _bin_cstr(data: PackedByteArray, pos: Array) -> Variant:
	var start: int = pos[0]
	var end := start
	while end < data.size() and data[end] != 0:
		end += 1
	if end >= data.size():
		return null
	pos[0] = end + 1
	return data.slice(start, end).get_string_from_utf8()


static func _bin_map(data: PackedByteArray, pos: Array) -> Variant:
	var result := {}
	while pos[0] < data.size():
		var t: int = data[pos[0]]
		pos[0] += 1
		if t == _BIN_END:
			return result
		var key: Variant = _bin_cstr(data, pos)
		if key == null:
			return null
		match t:
			_BIN_MAP:
				var child: Variant = _bin_map(data, pos)
				if child == null:
					return null
				result[key] = child
			_BIN_STRING:
				var s: Variant = _bin_cstr(data, pos)
				if s == null:
					return null
				result[key] = s
			_BIN_INT32, _BIN_FLOAT32:
				if pos[0] + 4 > data.size():
					return null
				if t == _BIN_INT32:
					result[key] = data.decode_s32(pos[0])
				else:
					result[key] = data.decode_float(pos[0])
				pos[0] += 4
			_BIN_UINT64, _BIN_INT64:
				if pos[0] + 8 > data.size():
					return null
				result[key] = data.decode_s64(pos[0])
				pos[0] += 8
			_:
				return null
	# Top level of shortcuts.vdf ends with two END bytes; running out at top level is fine.
	return result
