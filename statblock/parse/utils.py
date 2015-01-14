import json
import re
from statblock.utils import split

def handle_list(object_type):
	def _handle_list_intern(statblock, token, data):
		lines = data['lines']
		content = " ".join([line.strip() for line in lines])
		fields = split(content, ";")
		if len(fields) > 1:
			raise Exception("; not yet supported in %s: %s" % (token, json.dumps(content)))
		parts = [create(object_type, name=part.strip()) for part in split(content)]
		name_token = token.lower().replace(" ", "_")
		statblock[name_token] = parts
	return _handle_list_intern

def yield_statblocks(lines, retlines):
	while len(lines) > 0:
		line = lines.pop(0)
		if line.startswith("{"):
			data = json.loads(line)
			if data.get("tag") in ["creature", "statblock"]:
				yield data
			retlines.append("%s\n" % json.dumps(data))
		else:
			retlines.append(line)

def create(element_type, subtype=None, **kwargs):
	element_type = element_type.lower().replace(" ", "_")
	element = {
		"type": element_type
	}
	if subtype:
		subtype = subtype.lower().replace(" ", "_")
		element["subtype"] = subtype
	for key in kwargs:
		if kwargs[key] != None or key == "value":
			element[key] = kwargs[key]
	return element

def create_modifier(modifier_type=None, **kwargs):
	if modifier_type:
		modifier_type = modifier_type.lower().replace(" ", "_")
		return create("modifier", modifier_type=modifier_type, **kwargs)
	else:
		return create("modifier", **kwargs)

def add_modifier(statblock, modifier):
	modifiers = statblock.setdefault("modifiers", [])
	modifiers.append(modifier)

def add_situational_modifiers(statblock, modifiers, bonus=0):
	for modifier in split(modifiers):
		m = re.match("([+-]?[0-9]+) (.*)", modifier.strip())
		if m:
			value = int(m.groups()[0]) - bonus
			situation = m.groups()[1]
			add_modifier(statblock, create_modifier(
				subtype="situational", value=value, situation=situation))
		else:
			add_modifier(statblock, create_modifier(
				subtype="situational", situation=modifier))

