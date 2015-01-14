import json
import re
from statblock.parse.utils import handle_list, yield_statblocks
from statblock.parse.utils import create, create_modifier, add_modifier
from statblock.parse.utils import add_situational_modifiers
from statblock.utils import split

def parse_statistics(lines):
	retlines = []
	for statblock in yield_statblocks(lines, retlines):
		source = statblock.setdefault("source", {})
		stats_source = source.setdefault("statistics", {})
		stats = statblock.setdefault("statistics", {})
		if stats_source:
			keys = stats_source.keys()
			for key in keys:
				data = stats_source[key]
				del stats_source[key]
				handler = _get_stat_handler(key)
				handler(stats, key, data)
		del source["statistics"]
		if len(stats) == 0:
			del statblock["statistics"]
	return retlines

def parse_gear(lines):
	retlines = []
	for statblock in yield_statblocks(lines, retlines):
		source = statblock.setdefault("source", {})
		gear = source.setdefault("gear", {})
		if gear:
			_handle_gear(statblock, "gear", gear)
		del source["gear"]
	return retlines

def _get_stat_handler(token):
	handlers = {
		"gear": _handle_gear,
		"combat gear": _handle_gear,
		"other gear": _handle_gear,
		"skills": _handle_skills,
		"feats": handle_list("feat"),
		"sq": handle_list("special_quality"),
		"languages": _handle_languages,
		"attack": _handle_attack,
		"attributes": _handle_attributes
	}
	if token in handlers:
		return handlers[token]
	else:
		raise Exception("Stat token not found: %s" % token)

def _handle_gear(statblock, token, data):
	lines = data['lines']
	content = " ".join([line.strip() for line in lines])
	gear = statblock.setdefault("gear", {})
	items = split(content)
	subgear = gear.setdefault(token, [])
	for item in items:
		subgear.append(create("gear", name=item.strip()))

def _handle_skills(statblock, token, data):
	lines = data['lines']
	content = " ".join([line.strip() for line in lines]).split(";")
	skills_line = content.pop(0)
	skills = {}
	for skill_line in split(skills_line):
		skill_line = skill_line.strip()
		name = None
		bonus = None
		m = re.match("^([A-Za-z ]*) ([+-]?[0-9]+)$", skill_line)
		if m:
			name = m.groups()[0]
			skill_name = name.lower().replace(" ", "_")
			bonus = int(m.groups()[1])
			skills[skill_name] = create("skill", value=bonus, name=name)
			continue
		m = re.match("^([A-Za-z ]*) \((.*?)\) ([+-]?[0-9]+)$", skill_line)
		if m:
			name = m.groups()[0]
			skill_name = name.lower().replace(" ", "_")
			subtype = m.groups()[1]
			bonus = int(m.groups()[2])
			subtype = subtype.replace(", and ", ", ").replace(" or ", ", ")
			for st in subtype.split(","):
				skills["%s_%s" % (skill_name, st.strip().replace(" ", "_"))] = create(
					"skill", value=bonus, name=name, subskill=st.strip())
			continue
		m = re.match("^([A-Za-z ]*) ([+-]?[0-9]+) \((.*?)\)$", skill_line)
		if m:
			name = m.groups()[0]
			skill_name = name.lower().replace(" ", "_")
			bonus = int(m.groups()[1])
			skill = create("skill", value=bonus, name=name)
			skills[skill_name] = skill
			modifiers = m.groups()[2]
			add_situational_modifiers(skill, modifiers, bonus)
			continue

	for line in content:
		if line.strip().startswith("Racial Modifiers "):
			line = line.replace("Racial Modifiers ", "")
			bonuses = split(line)
			for bonus in bonuses:
				m = re.match("([+-]?[0-9]+) (.*)", bonus.strip())
				if m:
					b = int(m.groups()[0])
					skill_name = m.groups()[1]
					skill = skills.setdefault(skill_name, create("skill", name=name))
					add_modifier(skill, create_modifier("racial", value=b))
				else:
					raise Exception("Can't parse: %s" % line)
		else:
			raise Exception("Unknown skill subsection: %s" % line)
	statblock["skills"] = skills

def _handle_languages(statblock, token, data):
	lines = data['lines']
	content = " ".join([line.strip() for line in lines])
	fields = split(content, ";")
	languages = split(fields[0])
	final = []
	for language in languages:
		final.append(create("language", name=language.strip()))
	if len(fields) > 1:
		others = split(fields[1])
		for other in others:
			final.append(create("language", "other", name=other.strip()))
	elif len(fields) > 2:
		raise Exception("I don't know how to handle this language list: %s" % json.dumps(content))
	statblock["languages"] = final

def _handle_attack(statblock, token, data):
	lines = data['lines']
	content = " ".join([line.strip() for line in lines])
	fields = [field.strip() for field in split(content, char=";")]
	for field in fields:
		m = re.match("(.*?) ([+-]?[0-9]+) \((.*?)\)", field)
		if m:
			name = m.groups()[0]
			name, subtype, abbrev = _get_attack_fields(name)
			bonus = int(m.groups()[1])
			modifiers = m.groups()[2]
			section = create(
				"attack", subtype, name=name, value=bonus, abbrev=abbrev)
			add_situational_modifiers(section, modifiers, bonus)
			statblock[name] = section
			continue
		m = re.match("(.*?) ([+-]?[0-9]+)", field)
		if m:
			name = m.groups()[0]
			name, subtype, abbrev = _get_attack_fields(name)
			bonus = int(m.groups()[1])
			statblock[name] = create(
				"attack", subtype, name=name, value=bonus, abbrev=abbrev)
		m = re.match("(.*?) -", field)
		if m:
			name = m.groups()[0]
			name, subtype, abbrev = _get_attack_fields(name)
			statblock[name] = create(
				"attack", subtype, name=name, value=None, abbrev=abbrev)

def _get_attack_fields(name):
	if name == "Base Atk":
		return "base_attack", "base", "base atk"
	elif name == "CMD":
		return "combat_maneuver_defense", "cmd", "cmd"
	elif name == "CMB":
		return "combat_maneuver_bonus", "cmb", "cmb"
	raise Exception("I don't recognize attack: %s" % name)

def _handle_attributes(statblock, token, data):
	lines = data['lines']
	content = " ".join([line.strip() for line in lines])
	for field in split(content):
		field = field.strip()
		m = re.match("^([A-Za-z]+) ([-0-9]+)$", field)
		if m:
			stat = m.groups()[0]
			stat, abbrev = _get_attribute_name(stat)
			value = m.groups()[1]
			if value == "-":
				value = None
			else:
				value = int(value)
			mod = "%s_mod" % abbrev
			mod_value = None
			if value:
				mod_value = int(value - 10) / 2
			statblock[abbrev] = create(
				"attribute", name=stat, value=value, abbrev=abbrev, mod=create(
					"attribute_modifier", name=mod, value=mod_value))
		else:
			raise Exception("Cannot parse Attributes: %s" % json.dumps(content))

def _get_attribute_name(name):
	if name == "Str":
		return "strength", "str"
	elif name == "Dex":
		return "dexterity", "dex"
	elif name == "Con":
		return "constitution", "con"
	elif name == "Int":
		return "intelligence", "int"
	elif name == "Wis":
		return "wisdom", "wis"
	elif name == "Cha":
		return "charisma", "cha"
	raise Exception("I don't recognize attribute: %s" % name)
