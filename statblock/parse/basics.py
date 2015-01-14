import re
from statblock.parse.utils import yield_statblocks
from statblock.parse.utils import create
from statblock.utils import split

def parse_basics(lines):
	lines = parse_alignment(lines)
	lines = parse_lines(lines)
	lines = parse_senses(lines)
	return lines

def parse_senses(lines):
	retlines = []
	for statblock in yield_statblocks(lines, retlines):
		source = statblock.setdefault("source", {})
		basics = statblock.setdefault("basics", {})
		senses_source = source.setdefault("senses", {})
		content = " ".join([sense.strip() for sense in senses_source.get("lines", [])])
		if content != "":
			parts = [part.strip() for part in split(content, ";")]
			parts = _handle_initiative(basics, parts)
			parts = _handle_senses(basics, parts)
			parts = _handle_perception(statblock, parts)
			if len(parts) > 0:
				raise Exception("Senses line contains unknown parts: %s" % content)
		del source["senses"]
	return retlines

def _handle_initiative(statblock, parts):
	retlines = []
	while len(parts) > 0:
		part = parts.pop()
		if part.strip().startswith("Init "):
			value = int(part[5:])
			statblock["initiative"] = create(
				"initiative", value=value)
		else:
			retlines.append(part)
	return retlines

def _handle_senses(statblock, parts):
	retlines = []
	while len(parts) > 0:
		part = parts.pop()
		if part.strip().startswith("Senses "):
			content = part[7:]
			sections = [p.strip() for p in split(content)]
			statblock["senses"] = [create("sense", name=s) for s in sections]
		else:
			retlines.append(part)
	return retlines

def _handle_perception(statblock, parts):
	retlines = []
	while len(parts) > 0:
		part = parts.pop()
		if part.strip().startswith("Perception "):
			value = int(part[11:])
			statistics = statblock.setdefault("statistics", {})
			skills = statistics.setdefault("skills", {})
			if skills.has_key("perception"):
				perception = skills["perception"]
				if perception.get("value") != value:
					raise Exception("Perception from skills line does not agree with senses line: %s " % part)
			else:
				skills["Perception"] = {"name": "Perception", "value": value}
		else:
			retlines.append(part)
	return retlines

def parse_alignment(lines):
	retlines = []
	for statblock in yield_statblocks(lines, retlines):
		source = statblock.setdefault("source", {})
		alignment = source.setdefault("alignment", {})
		basics = statblock.setdefault("basics", {})
		if alignment:
			if _is_haunt(alignment):
				_parse_haunt(basics, alignment)
			else:
				_parse_alignment(basics, alignment)
		del source["alignment"]
	return retlines

def _parse_alignment(statblock, data):
	content = " ".join([l.strip() for l in data["lines"]])
	if content.find("(") > -1:
		content, subtypes = content.split("(")
		subtypes = subtypes[:-1]
		statblock["creature_subtypes"] = [s.strip() for s in split(subtypes)]
	parts = content.split()
	align = parts.pop(0)
	if not validate_alignment(align):
		raise Exception("Don't recognize alignment: %s" % align)
	statblock["alignment"] = create("alignment", value=align)
	statblock["size"] = create_size(parts.pop(0))
	creature_type = " ".join(parts)
	if not validate_creature_type(creature_type):
		raise Exception("Creature Type unrecognized: %s" % creature_type)
	statblock["creature_type"] = creature_type

def _is_haunt(alignment):
	for line in alignment["lines"]:
		if line.find(" haunt ") > -1:
			return True
	return False

def _parse_haunt(statblock, haunt):
	haunt_source = haunt["lines"].pop(0)
	caster = None
	if len(haunt["lines"]) > 0:
		caster = haunt["lines"].pop(0)
	if len(haunt["lines"]) > 0:
		raise Exception("Don't know how to parse haunt: %s" % haunt)
	haunt = statblock.setdefault("haunt", create("haunt"))
	if haunt_source.find("(") > -1:
		haunt_source, notes = haunt_source.split("(")
		notes = notes.strip().replace(")", "")
		haunt["notes"] = notes
	parts = haunt_source.split()
	align = parts.pop(0)
	if not validate_alignment(align):
		raise Exception("Don't recognize alignment: %s" % align)
	haunt["alignment"] = create("alignment", value=align)
	haunt["haunt_type"] = " ".join(parts)
	if caster:
		if caster.startswith("Caster Level "):
			caster = caster.strip()
			caster = caster[13:-2]
			haunt["caster_level"] = create("caster_level", value=int(caster))
		else:
			raise Exception(
				"I don't know how to handle this caster level: %s" % caster)

def parse_lines(lines):
	retlines = []
	for statblock in yield_statblocks(lines, retlines):
		source = statblock.setdefault("source", {})
		lines = source.setdefault("lines", [])
		content = " ".join([l.strip() for l in lines])
		if content:
			m = re.match("^(.*) \((.*)\)$", content)
			if m:
				content, book = m.groups()
				statblock["book"] = book
			parts = content.split()
			if len(parts) > 0:
				basics = statblock.setdefault("basics", {})
				if parts[0].lower() in ["male", "female"]:
					basics["sex"] = parts.pop(0)
				_parse_classes(basics, parts)
				basics["race"] = " ".join(parts)
		del source["lines"]
	return retlines

def _parse_classes(creature, parts):
	class_parts = []
	while parts[-1][0].isdigit():
		class_parts.insert(0, parts.pop())
	if len(class_parts) > 0:
		class_parts.insert(0, parts.pop())
	if parts[-1] == "of":
		class_parts.insert(0, parts.pop())
		class_parts.insert(0, parts.pop())
	class_source = " ".join(class_parts)
	classes = [s.strip() for s in split(class_source, char="/")]
	cc = None
	for pc_class in classes:
		m = re.match("^(.*) (\d+)$", pc_class)
		if m:
			name, value = m.groups()
			cc = creature.setdefault("classes", [])
			cc.append(create("class", name=name, value=int(value)))
		else:
			raise Exception("I don't recognize class: %s" % pc_class)

def validate_alignment(align):
	if align in ["LG", "LN", "LE", "NG", "N", "NE", "CG", "CN", "CE"]:
		return True
	return False

def create_size(size):
	sizes = [
		"fine", "diminutive", "tiny", "small", "medium", "large", "huge",
		"gargantuan", "colossal"]
	if size.lower() in sizes:
		return create("creature_size", value=size)
	else:
		raise Exception("Size unrecognized: %s" % size)

def validate_creature_type(ctype):
	ctypes = [
		"aberration", "animal", "construct", "dragon", "fey", "humanoid",
		"magical beast", "monstrous humanoid", "ooze", "outsider", "plant",
		"undead", "vermin"]
	if ctype.lower() in ctypes:
		return True
	return False
