import json
import copy
import re
import sys
from statblock.parse.utils import handle_list, yield_statblocks
from statblock.parse.utils import create
from statblock.utils import split

def parse_offense(lines):
	retlines = []
	for statblock in yield_statblocks(lines, retlines):
		source = statblock.setdefault("source", {})
		offense_source = source.setdefault("offense", {})
		offense = statblock.setdefault("offense", {})
		keys = offense_source.keys()
		print json.dumps(offense_source, indent=2)
		for key in keys:
			data = offense_source[key]
			del offense_source[key]
			handler = _get_offense_handler(key)
			handler(offense, key, data)
		for key in ["melee", "ranged", "space", "speed", "special attacks"]:
			if source.has_key(key):
				data = source[key]
				del source[key]
				handler = _get_offense_handler(key)
				handler(offense, key, data)

		del source["offense"]
	return retlines

def _get_offense_handler(token):
	handlers = {
		"melee": _handle_weapons,
		"ranged": _handle_weapons,
		"speed": _handle_speed,
		"space": _handle_space,
		"special attacks": handle_list("special_attack")
	}
	if token in handlers:
		return handlers[token]
	elif token.find("spells known") > -1:
		return _handle_spells
	elif token.find("spells prepared") > -1:
		return _handle_spells
	elif token.find("extracts prepared") > -1:
		return _handle_spells
	elif token.find("spell-like abilities") > -1:
		return _handle_spells
	elif token.find("spell-like ability") > -1:
		return _handle_spells
	else:
		raise Exception("Offense token not found: %s" % token)

def _handle_spells(statblock, token, data):
	section = statblock.setdefault(token, create("spell_source"))
	lines = data["lines"]
	lines = _generate_spell_fields(lines)
	lines = _split_spell_fields(lines)
	lines = _handle_cl(section, lines)
	section["spell_lists"] = []
	lines = _handle_spell_notes(section, lines)
	lines = _split_spells(section, lines)
	if len(lines) > 0:
		raise Exception("Unparsed spell data: %s" % json.dumps(lines, indent=2))

def _handle_spell_notes(section, lines):
	retlines = []
	for line in lines:
		append = True
		for s in ["Thassilonian Specialization", "Thassilonian Specialist", "Opposition Schools", "Prohibited Schools ", "D ", "Domain ", "Domains ", "Patron ", "Bloodline ", "Mystery ", "M "]:
			if line.startswith(s):
				if s not in ["D ", "M "]:
					data = line[len(s):].strip()
					key = s.lower().strip()
					if data.find(",") > -1:
						data = [d.strip() for d in split(data)]
					if s == "Domain ":
						key = "domains"
						data = [data]
					if s == "Thassilonian Specialist":
						key = "thassilonian specialization"
					section[key] = data
				append = False
		if append:
			retlines.append(line)
	return retlines

def _split_spells(section, lines):
	retlines = []
	for line in lines:
		m = re.match("^(\d)[snrt][tdh]-", line)
		if m:
			level = int(m.groups()[0])
			_add_spells(line, section, level)
			continue
		if line.startswith("0 (at will)-"):
			level = 0
			_add_spells(line, section, level, "at will")
			continue
		m = re.match("^(\d)[snrt][tdh] \((\d+)/day\)-", line)
		if m:
			level = int(m.groups()[0])
			per_day = int(m.groups()[1])
			_add_spells(line, section, level, per_day, "day")
			continue
		if line.startswith("Constant-"):
			_add_spells(line, section, freq="constant")
			continue
		if line.startswith("At will-") or line.startswith("At Will-"):
			_add_spells(line, section, freq="at will")
			continue
		m = re.match("^(\d+)/hour-", line)
		if m:
			per_day = int(m.groups()[0])
			_add_spells(line, section, freq=per_day, freq_period="hour")
			continue
		m = re.match("^(\d+)/day-", line)
		if m:
			per_day = int(m.groups()[0])
			_add_spells(line, section, freq=per_day, freq_period="day")
			continue
		m = re.match("^(\d+)/week-", line)
		if m:
			per_week = int(m.groups()[0])
			_add_spells(line, section, freq=per_day, freq_period="week")
			continue
		retlines.append(line)
	return retlines

def _add_spells(line, section, level=None, freq=None, freq_period=None):
	parts = line.split("-")
	parts.pop(0)
	spells = [s.strip() for s in split("-".join(parts))]
	spell = create("spell")
	spell_list = create("spell_list", spells=[])
	if level != None:
		spell_list["level"] = level
		spell["level"] = level
	if freq:
		spell_list["frequency"] = freq
	if freq_period:
		spell_list["frequency period"] = freq_period
	for spell_source in spells:
		_parse_spell(spell_source, spell, spell_list)
	section["spell_lists"].append(spell_list)

def _parse_spell(spell_source, default, spell_list):
	spell = copy.copy(default)
	m = re.match("(.*) \((.*)\)", spell_source)
	count = 1
	if m:
		spell["name"] = m.groups()[0]
		notes = [s.strip() for s in split(m.groups()[1])]
		while len(notes) > 0:
			note = notes.pop(0)
			if note.startswith("DC "):
				dc = note[3:]
				dc_notes = None
				if dc.find(";"):
					parts = split(dc, char=";")
					dc = parts.pop(0)
					dc_notes = parts
				dc = int(dc)
				spell["dc"] = {"value": dc}
				if dc_notes:
					spell["dc"]["notes"] = dc_notes
			elif note.isdigit():
				count = int(note)
			else:
				spell["notes"] = note
	else:
		spell["name"] = spell_source
	if spell["name"].endswith("D"):
		spell["name"] = spell["name"][:-1]
		spell["domain"] = True
	if spell["name"].endswith("M"):
		spell["name"] = spell["name"][:-1]
		spell["mythic"] = True
	for i in range(count):
		spell_list["spells"].append(spell)

def _generate_spell_fields(lines):
	retlines = []
	for line in lines:
		line = line.strip()
		append = False
		for s in ["Constant-", "At will-", "Thassilonian Specialization", "Thassilonian Specialist", "Opposition Schools", "D ", "Domain ", "Domains ", "Patron ", "Bloodline ", "Mystery ", "M "]:
			if line.startswith(s):
				append = True
				continue
		if append:
			retlines.append(line)
			continue
		m = re.match("^\d[snrt][tdh]", line)
		if m:
			retlines.append(line)
			continue
		m = re.match("^\d+/[dw][a-z]+", line)
		if m:
			retlines.append(line)
			continue
		if line.startswith("(CL "):
			retlines.append(line)
			continue
		if line.startswith("0 (at will)-"):
			retlines.append(line)
			continue
		retlines[-1] = " ".join([retlines[-1], line])
	return retlines

def _split_spell_fields(lines):
	retlines = []
	for line in lines:
		if line.find(";") > -1:
			parts = split(line, char=";")
			for part in parts:
				retlines.append(part.strip())
		else:
			retlines.append(line)
	return retlines

def _handle_cl(section, lines):
	line = lines.pop(0)
	m = re.match("\((CL .*?)\)", line)
	if m:
		cl = m.groups()[0]
		pieces = split(cl, char=";")
		for piece in pieces:
			piece = piece.strip()
			m = re.match("CL (\d+)[snrt][tdh]", piece)
			if m:
				section["caster_level"] = create(
					"caster_level", value=int(m.groups()[0]))
				continue
			m = re.match("(\d+)% spell failure", piece)
			if m:
				section["spell_failure"] = create(
					"spell_failure", value=int(m.groups()[0]))
				continue
			m = re.match("concentration ([+-]?\d+)", piece)
			if m:
				section["concentration"] = create(
					"concentration", value=int(m.groups()[0]))
				continue
			section["notes"] = line
		parts = line.split(")")
		parts.pop(0)
		line = ")".join(parts).strip()
		if line == "":
			return lines
		else:
			lines.insert(0, line)
			return lines
	raise Exception("Spell block has unexpected format: %s" % line)

def _handle_weapons(statblock, token, data):
	content = " ".join([d.strip() for d in data["lines"]])
	section = statblock.setdefault(token, [])
	if content.find(" or "):
		content.replace(" or ", "`")
	for weapon_set_source in split(content, char="`"):
		weapon_set_source = weapon_set_source.replace("`", " or ")
		weapon_set = []
		section.append(weapon_set)
		for weapon in split(weapon_set_source):
			weapon = weapon.strip()
			m = re.match("(\d+) (.*) ([0-9/+-]+) \((.*)\)", weapon)
			if m:
				count = int(m.groups()[0])
				name = m.groups()[1]
				if name.endswith("s"):
					name = name
				to_hit = m.groups()[2]
				damage = m.groups()[3]
				w = _generate_weapon(name, to_hit, damage)
				w["count"] = count
				weapon_set.append(w)
				continue
			m = re.match("(.*) ([0-9/+-]+) \((.*)\)", weapon)
			if m:
				name = m.groups()[0]
				to_hit = m.groups()[1]
				damage = m.groups()[2]
				w = _generate_weapon(name, to_hit, damage)
				weapon_set.append(w)
				continue
			m = re.match("(.*) ([0-9/+-]+)", weapon)
			if m:
				name = m.groups()[0]
				to_hit = m.groups()[1]
				w = _generate_weapon(name, to_hit)
				weapon_set.append(w)
				continue
			m = re.match("(.*) ([0-9/+-]+)", weapon)
			if m:
				name = m.groups()[0]
				to_hit = m.groups()[1]
				w = _generate_weapon(name, to_hit)
				weapon_set.append(w)
				continue
			m = re.match("(.*) \((.*)\)", weapon)
			if m:
				name = m.groups()[0]
				damage = m.groups()[1]
				w = _generate_weapon(name, "", damage)
				weapon_set.append(w)
				continue
			raise Exception("Don't know how to parse weapon: %s" % json.dumps(weapon))

def _generate_weapon(name, to_hit, damage=None):
	w = {
		"name": name,
	}
	if len(to_hit) > 0:
		to_hit = [int(t) for t in to_hit.split("/")]
		w["to-hit"] =  []
		for t in to_hit:
			w["to-hit"].append({"value": t})
	if damage:
		w["damage"] = {}
		damage = _damage_get_die(w, damage)
		damage = _damage_get_plus(w, damage)
		damage = _damage_get_crit_range(w, damage)
		damage = _damage_get_crit_mult(w, damage)
		if damage.strip() != "":
			w["description"] = damage.strip()
	return w

def _damage_get_die(weapon, damage):
	m = re.match("^(\d+[Dd]\d+).*", damage)
	if m:
		die = m.groups()[0]
		weapon["damage"]["die"] = die
		return damage[len(die):]
	return damage

def _damage_get_plus(weapon, damage):
	m = re.match("^([+-]\d+).*", damage)
	if m:
		plus = m.groups()[0]
		weapon["damage"]["plus"] = {"value": int(plus)}
		return damage[len(plus):]
	return damage

def _damage_get_crit_range(weapon, damage):
	m = re.match("^/([0-9-]+).*", damage)
	if m:
		crange = m.groups()[0]
		weapon["damage"]["crit_range"] = {"value": crange}
		return damage[len(crange)+1:]
	if weapon["damage"].has_key("die"):
		weapon["damage"]["crit_range"] = "20"
	return damage

def _damage_get_crit_mult(weapon, damage):
	m = re.match(u"^/\u00d7([0-9]).*", damage)
	if m:
		mult = m.groups()[0]
		weapon["damage"]["crit_mult"] = {"value": mult}
		return damage[len(mult)+2:]
	if weapon["damage"].has_key("die"):
		weapon["damage"]["crit_mult"] = "1"
	return damage

def _handle_speed(statblock, token, data):
	content = " ".join([d.strip() for d in data["lines"]])
	statblock["speed"] = [create("movement", name=c.strip()) for c in split(content)]

def _handle_space(statblock, token, data):
	content = " ".join([d.strip() for d in data["lines"]])
	space = content
	if content.find(";"):
		parts = split(space, char=";")
		space = parts.pop(0)
		for part in parts:
			part = part.strip()
			if part.startswith("Reach "):
				statblock["reach"] = part[6:]
			else:
				raise Exception("Space token not recognized: %" % content)
	statblock["space"] = space
