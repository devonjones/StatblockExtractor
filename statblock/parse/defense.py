import json
import re
import sys
from statblock.parse.utils import handle_list, yield_statblocks
from statblock.parse.utils import create, create_modifier
from statblock.parse.utils import add_situational_modifiers
from statblock.utils import split

def parse_defense(lines):
	retlines = []
	for statblock in yield_statblocks(lines, retlines):
		source = statblock.setdefault("source", {})
		defense_source = source.setdefault("defense", {})
		defense = statblock.setdefault("defense", {})
		keys = defense_source.keys()
		for key in keys:
			data = defense_source[key]
			del defense_source[key]
			handler = _get_defense_handler(key)
			handler(defense, key, data)
		del source["defense"]
		if len(defense) == 0:
			del statblock["defense"]
	return retlines

def _get_defense_handler(token):
	handlers = {
		"ac": _handle_ac,
		"saves": _handle_saves,
		"hp": _handle_hp,
		"weaknesses": handle_list("weakness"),
		"defenses": _handle_defenses
	}
	if token in handlers:
		return handlers[token]
	else:
		raise Exception("Defense token not found: %s" % token)

def _handle_ac(statblock, token, data):
	content = " ".join([l.strip() for l in data["lines"]])
	parts = split(content, char=";")
	ac = statblock.setdefault("ac", {})
	ac_part = parts.pop(0)
	try:
		_handle_ac_components(ac, ac_part)
	except Exception, e:
		sys.stderr.write("%s\n" % json.dumps(content, indent=2))
		raise e
	if len(parts) > 0:
		ac["abilities"] = [p.strip() for p in parts]

def _handle_ac_components(ac, line):
	parts = line.split("(")
	armor = parts.pop(0)
	_parse_armor(ac, armor)
	pieces = "(".join(parts)
	if pieces.endswith(")"):
		pieces = pieces[:-1]
	pieces = pieces.strip()
	if pieces.find(";") > -1:
		sitmods = pieces.split(";")
		pieces = sitmods.pop(0)
		ac_modifiers = _parse_ac_modifiers(pieces)
		_apply_ac_modifiers(ac, ac_modifiers, sitmods)
	else:
		ac_modifiers = _parse_ac_modifiers(pieces)
		_apply_ac_modifiers(ac, ac_modifiers)

def _parse_armor(ac, line):
	parts = [l.strip() for l in split(line)]
	ac["base"] = {
		"value": int(parts.pop(0)), "name": "base", "type": "armor_class"}
	while len(parts) > 0:
		p = parts.pop()
		if p.startswith("touch"):
			ac["touch"] = {
				"value": int(p.replace("touch", "")),
				"name": "touch", "type": "armor_class"}
		elif p.startswith("flat-footed"):
			ac["flat-footed"] = {
				"value": int(p.replace("flat-footed", "")),
				"name": "flat-footed", "type": "armor_class"}
		else:
			raise Exception("I don't know how to parse armor: %s" % line)

def _parse_ac_modifiers(pieces):
	parts = [p.strip() for p in split(pieces)]
	results = {}
	for part in parts:
		m = re.match("^([-+]?\d+) (.*)", part)
		if m:
			bonus = int(m.groups()[0])
			name = m.groups()[1]
			results[name] = bonus
			continue
		raise Exception("Don't know how to parse: %s" % pieces)
	return results

def _apply_ac_modifiers(ac, ac_modifiers, sit_ac_modifiers=None):
	base = ac["base"]
	base["modifiers"] = [{
		"value": 10, "type": "modifier", "modifier_type": "base"}]
	touch = ac["touch"]
	touch["modifiers"] = [{
		"value": 10, "type": "modifier", "modifier_type": "base"}]
	ff = ac["flat-footed"]
	ff["modifiers"] = [{
		"value": 10, "type": "modifier", "modifier_type": "base"}]
	for mod in ac_modifiers:
		name = mod
		source = None
		if name == "Dex":
			name = "dex mod"
			source = "statistics.dex.mod.value"
		base["modifiers"].append(create_modifier(
			name, value=ac_modifiers[mod], source=source))
		if mod not in ["armor", "shield", "natural", "mage armor"]:
			touch["modifiers"].append(create_modifier(
				name, value=ac_modifiers[mod], source=source))
		if mod not in ["Dex", "dodge"] or (mod == "Dex" and ac_modifiers[mod] < 0):
			bonus = None
			if mod == "Dex":
				bonus = False
			ff["modifiers"].append(create_modifier(
				name, value=ac_modifiers[mod], source=source, bonus=bonus))
	try:
		_check_ac(base)
		_check_ac(touch)
		_check_ac(ff)
	except Exception, e:
		sys.stderr.write("%s\n" % json.dumps(ac, indent=2))
		raise e
	if sit_ac_modifiers:
		for mod in sit_ac_modifiers:
			name = mod.lower()
			if has_s(mod, "dex") or has_s(mod, "dodge"):
				add_situational_modifiers(base, mod)
				add_situational_modifiers(touch, mod)
			elif has_s(mod, "armor") or has_s(mod, "shield") or has_s(mod, "natural"):
				add_situational_modifiers(base, mod)
				add_situational_modifiers(ff, mod)
			else:
				add_situational_modifiers(base, mod)
				add_situational_modifiers(touch, mod)
				add_situational_modifiers(ff, mod)

def has_s(s, m):
	if s.find(m) > -1:
		return True
	return False

def _check_ac(ac):
	value = ac["value"]
	mod_total = 0
	for mod in ac["modifiers"]:
		mod_total = mod_total + mod["value"]
	if value != mod_total:
		raise Exception("Ac does not total correctly: %s != %s %s" % (value, mod_total, json.dumps(ac)))

def _handle_saves(statblock, token, data):
	content = " ".join([l.strip() for l in data["lines"]])
	saves = statblock.setdefault("saves", {})
	parts = [s.strip() for s in split(content, char=";")]
	saves_source = [s.strip() for s in split(parts.pop(0))]
	modifiers = ";".join(parts)
	for save in saves_source:
		m = re.match("^(.*) ([-+]?\d+)$", save)
		if m:
			name, value = m.groups()
			name = name.lower()
			value = int(value)
			if name == "ref":
				name = "reflex"
			elif name == "fort":
				name = "fortitude"
			saves[name] = create("save", name=name, value=value)
			add_situational_modifiers(saves[name], modifiers)
			continue
		m = re.match("^(.*) ([-+]?\d+) \((.*)\)$", save)
		if m:
			name, value, specific_modifiers = m.groups()
			name = name.lower()
			value = int(value)
			if name == "ref":
				name = "reflex"
			elif name == "fort":
				name = "fortitude"
			saves[name] = create("save", name=name, value=int(m.groups()[1]))
			add_situational_modifiers(saves[name], modifiers)
			add_situational_modifiers(saves[name], specific_modifiers, value)
			continue
		raise Exception("Don't know how to parse saves: %s" % content)

def _handle_defenses(statblock, token, data):
	content = " ".join([l.strip() for l in data["lines"]])
	chunks = [s.strip() for s in split(content, char=";")]
	for da in chunks:
		if da.startswith("Defensive Abilities "):
			_handle_defensive_abilities(statblock, da)
		elif da.startswith("DR "):
			_handle_dr(statblock, da)
		elif da.startswith("Immune "):
			handle_list("immune")(statblock, "immune", {"lines": [da[7:]]})
		elif da.startswith("Resist "):
			_handle_resist(statblock, da)
		elif da.startswith("SR "):
			_handle_sr(statblock, da)
		else:
			raise Exception("I don't recognize this defense: %s" % json.dumps(da))

def _handle_defensive_abilities(statblock, data):
	abilities = [s.strip() for s in split(data[20:])]
	da_s = statblock.setdefault("defensive abilities", {})
	for ability in abilities:
		m = re.match("^(.*) ([-+]?\d+)$", ability)
		if m:
			name = m.groups()[0]
			bonus = int(m.groups()[1])
			da_s["name"] = create("defensive_ability", name=name, value=bonus)
		else:
			da_s["name"] = create("defensive_ability", name=ability)

def _handle_dr(statblock, data):
	drs = [s.strip() for s in data[3:].split(', DR')]
	for dr in drs:
		value, overcome = dr.split("/")
		dr_section = statblock.setdefault("damage_reduction", [])
		dr_section.append(create(
			"damage_reduction", value=int(value), overcome=overcome))

def _handle_resist(statblock, data):
	resists = [s.strip() for s in split(data[7:])]
	for resist in resists:
		m = re.match("(.*) (\d+) \((.*)\)", resist)
		if m:
			name, value, notes = m.groups()
			resist_section = statblock.setdefault("resistances", [])
			resist_section.append(create(
				"resistance", name=name, value=int(value), notes=notes))
			continue
		m = re.match("(.*) (\d+)", resist)
		if m:
			name, value = m.groups()
			resist_section = statblock.setdefault("resistances", [])
			resist_section.append(create(
				"resistance", name=name, value=int(value)))
			continue
		raise Exception("Don't know how to parse resist: %s" % data)

def _handle_sr(statblock, data):
	sr_s = [s.strip() for s in split(data[3:])]
	for sr in sr_s:
		m = re.match("(\d+) \((.*)\)", sr)
		if m:
			value, notes = m.groups()
			sr_section = statblock.setdefault("spell_resistances", [])
			sr_section.append(create(
				"spell_resistance", value=int(value), notes=notes))
			continue
		m = re.match("(\d+) (.*)", sr)
		if m:
			value, notes = m.groups()
			sr_section = statblock.setdefault("spell_resistances", [])
			sr_section.append(create(
				"spell_resistance", value=int(value), notes=notes))
			continue
		resist_section = statblock.setdefault("spell_resistances", [])
		resist_section.append(create("spell_resistance", value=int(sr)))

def _handle_hp(statblock, token, data):
	content = " ".join([l.strip() for l in data["lines"]])
	parts = [s.strip() for s in split(content, char=";")]
	hp_source = parts.pop(0)
	hp = statblock.setdefault("hit_points", create("hit_points"))
	hp_source = hp_source.replace(" each", "")
	m = re.match("(\d+) \((.*)\)", hp_source)
	if m:
		hit_points, hit_dice = m.groups()
		hp["value"] = int(hit_points)
		m = re.match("(\d+) HD; ([0-9d+]+)([-+]\d+)", hit_dice)
		if m:
			hd, dice, plus = m.groups()
			hp["hit_dice"] = create("hit_dice", value=int(hd))
			hp["dice"] = dice
			hp["plus"] = create("hp_plus", value=int(plus))
		else:
			m = re.match("([0-9]+)d([0-9]+)([-+]\d+)", hit_dice)
			if m:
				count, d_type, plus = m.groups()
				hp["hit_dice"] = create("hit_dice", value=int(count))
				hp["dice"] = "%sd%s" % (count, d_type)
				hp["plus"] = create("hp_plus", value=int(plus))
			else:
				m = re.match("([0-9]+)d([0-9]+)", hit_dice)
				if m:
					count, d_type = m.groups()
					hp["hit_dice"] = create("hit_dice", value=int(count))
					hp["dice"] = "%sd%s" % (count, d_type)
				else:
					raise Exception(
						"Don't know how to parse hit dice: %s" % json.dumps(content))
	else:
		raise Exception(
			"Don't know how to parse hp: %s" % json.dumps(content))
	if len(parts) > 0:
		healing = [h.strip() for h in split(parts.pop(0))]
		_handle_healing(hp, healing)
	if len(parts) > 0:
		raise Exception(
			"Don't know how to parse hp line: %s" % json.dumps(content))

def _handle_healing(hp, healing):
	for h in healing:
		m = re.match("(.*) (\d+) \((.*)\)", h)
		if m:
			name, value, notes = m.groups()
			heal_section = hp.setdefault("healing", [])
			heal_section.append(create(
				"healing_ability",
				name=name, value=int(value), notes=notes))
			continue
		m = re.match("(.*) (\d+)", h)
		if m:
			name, value = m.groups()
			heal_section = hp.setdefault("healing", [])
			heal_section.append(create(
				"healing_ability", name=name, value=int(value)))

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
		weapon["damage"]["plus"] = create("damage_plus", value=int(plus))
		return damage[len(plus):]
	return damage
