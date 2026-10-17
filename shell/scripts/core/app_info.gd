## Reader for Steam's binary app metadata cache, appcache/appinfo.vdf (read-only).
## Only common/name and common/type are extracted, and only for the app ids asked for:
## every other entry is skipped by its size field without being read, so a file of
## tens of MB costs a header walk, not a parse.
##
## Layout (SteamDatabase/SteamAppInfo, ValvePython vdf):
##   header   u32 magic, u32 universe, [v29: i64 offset of the string table]
##   entry    u32 appid (0 = end), u32 size (bytes after this field), u32 info_state,
##            u32 last_updated, u64 pics_token, 20 B sha1(text), u32 change_number,
##            [v28+: 20 B sha1(binary)], then binary KeyValues {"appinfo": {"common": ...}}
##   v29      KeyValues keys are i32 indices into the string table at the header offset:
##            u32 count, then count NUL-terminated strings.
## Formats: v27 0x07564427, v28 0x07564428, v29 0x07564429. Anything else, or a broken
## entry, ends the walk with what was read so far (error set), never an exception.
class_name SteamAppInfo
extends RefCounted

const MAGIC_V27 := 0x07564427
const MAGIC_V28 := 0x07564428
const MAGIC_V29 := 0x07564429

var version := 0
var error := ""
var entries := 0       # entries walked (diagnostics)
var parse_ms := 0


## {appid: {"name": String, "type": String (lower case)}} for the wanted ids found in the
## file (wanted: {appid: anything}; empty = every app, only for tests/diagnostics).
func read(path: String, wanted: Dictionary = {}) -> Dictionary:
	var t0 := Time.get_ticks_msec()
	var out := {}
	error = ""
	entries = 0
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		error = "missing"
		return out
	var length := f.get_length()
	if length < 12:
		error = "short"
		return out
	var magic := f.get_32()
	f.get_32()  # universe
	var head_extra := 0
	match magic:
		MAGIC_V27:
			version = 27
			head_extra = 40
		MAGIC_V28:
			version = 28
			head_extra = 60
		MAGIC_V29:
			version = 29
			head_extra = 60
		_:
			version = 0
			error = "unsupported-format:%x" % magic
			return out
	var end := length
	var keys := {}  # v29: string-table index -> name, only for the names we look for
	if version == 29:
		if length < 16:
			error = "short"
			return out
		var table_at := f.get_64()
		if table_at < 16 or table_at >= length:
			error = "bad-string-table"
			return out
		keys = _string_table(f, table_at, length)
		if keys.is_empty():
			error = "bad-string-table"
			return out
		end = table_at
		f.seek(16)
	var remaining := wanted.size()
	while f.get_position() + 4 <= end:
		var at := f.get_position()
		var appid := f.get_32()
		if appid == 0:
			break
		if at + 8 > end:
			error = "truncated"
			break
		var size := f.get_32()
		var next := at + 8 + size
		if size < head_extra or next > end:
			error = "truncated"
			break
		entries += 1
		if wanted.is_empty() or wanted.has(appid):
			f.seek(at + 8 + head_extra)
			var info := _common(f.get_buffer(size - head_extra), keys)
			if not info.is_empty():
				out[appid] = info
			if not wanted.is_empty():
				remaining -= 1
				if remaining <= 0:
					break
		f.seek(next)
	parse_ms = Time.get_ticks_msec() - t0
	return out


## v29 string table -> {index: name} for the few key names this reader needs. Read in
## chunks and stopped once all are found: the table holds every key of every app
## (depot ids included, often 100k+ strings), the names needed are among the first.
static func _string_table(f: FileAccess, at: int, length: int) -> Dictionary:
	if at + 4 > length:
		return {}
	f.seek(at)
	var count := f.get_32()
	var want := ["appinfo", "common", "name", "type"]
	var out := {}
	var buf := PackedByteArray()
	var p := 0
	var i := 0
	while i < count:
		var z := buf.find(0, p)
		if z < 0:
			if f.get_position() >= length:
				break
			buf = buf.slice(p) + f.get_buffer(mini(65536, length - f.get_position()))
			p = 0
			continue
		var n := z - p
		# only these lengths and first letters can match: the rest is skipped undecoded
		if n >= 4 and n <= 7 and (buf[p] == 0x61 or buf[p] == 0x63 or buf[p] == 0x6E or buf[p] == 0x74):
			var s := buf.slice(p, z).get_string_from_utf8()
			if want.has(s):
				out[i] = s
				if out.size() == want.size():
					break
		p = z + 1
		i += 1
	return out


## Walks one entry's binary KeyValues for appinfo/common/{name,type}; stops at the end
## of "common". keys: v29 index table (empty for v27/v28, whose keys are inline strings).
static func _common(b: PackedByteArray, keys: Dictionary) -> Dictionary:
	var v29 := not keys.is_empty()
	var n := b.size()
	var p := 0
	var path: Array = []   # names of the maps we are in; "" for maps that do not matter
	var name := ""
	var type := ""
	var in_common := false
	while p < n:
		var t := b[p]
		p += 1
		if t == 0x08 or t == 0x0B:
			if path.is_empty():
				break
			if in_common and path.size() == 2:
				break  # end of common
			path.pop_back()
			continue
		var key := ""
		if v29:
			if p + 4 > n:
				break
			key = keys.get(b.decode_s32(p), "")
			p += 4
		else:
			var z := b.find(0, p)
			if z < 0:
				break
			if path.size() <= 2 and z - p <= 8:
				key = b.slice(p, z).get_string_from_utf8()
			p = z + 1
		match t:
			0x00:
				var depth := path.size()
				if (depth == 0 and key == "appinfo") or (depth == 1 and path[0] == "appinfo" and key == "common"):
					path.append(key)
					in_common = depth == 1
				else:
					path.append("")
			0x01:
				var z2 := b.find(0, p)
				if z2 < 0:
					break
				if in_common and path.size() == 2 and (key == "name" or key == "type"):
					var v := b.slice(p, z2).get_string_from_utf8()
					if key == "name":
						name = v
					else:
						type = v.to_lower()
				p = z2 + 1
			0x02, 0x03, 0x04, 0x06:
				p += 4
			0x07, 0x0A:
				p += 8
			0x05:  # wide string: UTF-16, NUL-terminated (two zero bytes on a 2-byte step)
				while p + 1 < n and (b[p] != 0 or b[p + 1] != 0):
					p += 2
				p += 2
			_:
				break
		if name != "" and type != "":
			break
	if name == "" and type == "":
		return {}
	return {"name": name, "type": type}
