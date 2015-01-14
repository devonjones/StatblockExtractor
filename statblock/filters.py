import sys
import re
import sh
import json
from statblock.utils import cap_name

def form_feed_filter(lines):
	retlines = []
	for line in lines:
		if "\f" in line:
			retlines.extend([field + "\n" for field in line.split("\f")])
		else:
			retlines.append(line)
	return retlines

def counter_filter(lines):
	retlines = []
	counter = 0
	for line in lines:
		if counter == 2 and line.strip() == "":
			counter = 0
			retlines = retlines[:-2]
		else:
			try:
				int(line.strip())
				counter += 1
			except:
				counter = 0
			retlines.append(line)
	return retlines

def page_split_filter(lines):
	retlines = []
	counter = 0
	lastline = None
	for line in lines:
		if line == lastline:
			if line.startswith("paizo.com"):
				retlines.pop()
				retlines.append("|PAGEEND|\n")
		else:
			retlines.append(line)
		lastline = line
	return retlines

def sidebar_filter(lines):
	line_buffer = []
	buffers = set()
	buffer_upper = True
	for line in lines:
		if line.strip() == "|PAGEEND|":
			if buffer_upper:
				_add_to_buffers(buffers, line_buffer)
			line_buffer = []
			buffer_upper = True
		else:
			line_buffer.append(line)
		if not line.strip().isupper() or line.strip().isdigit():
			if line.strip() != "":
				buffer_upper = False
	_buffer_all_the_things(buffers)
	skip = -1
	retlines = []
	for i in range(len(lines)):
		for b in buffers:
			buf = list(b)
			if lines[i:i+len(buf)] == buf:
				if skip < i+len(buf):
					skip = i+len(buf)
		if i > skip:
			retlines.append(lines[i])
	return retlines

def _add_to_buffers(buffers, lines):
	if len(lines) == 0:
		return
	while lines[0].strip() == "":
		lines.pop(0)
		if len(lines) == 0:
			return
	while lines[-1].strip() == "":
		lines.pop()
		if len(lines) == 0:
			return
	buffers.add(tuple(lines))

def _buffer_all_the_things(buffers):
	oneline = [b for b in buffers if len(b) == 1]
	newbuff = []
	for b in buffers:
		buf = list(b)
		for o in oneline:
			if o != b:
				if b[0].strip() == o[0].strip():
					buf.pop(0)
					newbuff.append(buf)
	for nb in newbuff:
		buffers.add(tuple(nb))

def location_filter(lines):
	retlines = []
	last = {}
	while len(lines) > 0:
		line = lines.pop(0)
		if re.match("[A-Z][0-9]+[a-z]? +.*", line.strip()) or re.match("[A-Z][0-9]+[a-z]? ?- ?[A-Z][0-9]+[a-z]? +.*", line.strip()):
			if line.find(" - ") > -1:
				line.replace(" - ", "-")
			parts = line.strip().split(" ")
			symbol = parts.pop(0)
			name = " ".join(parts)
			if name.isupper():
				location = {"symbol": symbol, "name": name.strip(), "tag": "event", "subtag": "location"}
				_pull_cr(location)
				sys.stderr.write(str(location) + "\n")
				_append_place(last, location, retlines)
			else:
				retlines.append(line)
		elif re.match("[A-Z][0-9]?[a-z]?\. +.*", line.strip()):
			if line.find(" - ") > -1:
				line.replace(" - ", "-")
			parts = line.strip().split(" ")
			symbol = parts.pop(0)
			symbol = symbol.replace(".", "")
			name = " ".join(parts)
			location = {"symbol": symbol, "name": name.strip(), "tag": "event", "subtag": "location"}
			_pull_cr(location)
			sys.stderr.write(str(location) + "\n")
			_append_place(last, location, retlines)
		elif re.match("EVENT:.*", line.strip()):
			parts = line.strip().split(":")
			symbol = parts.pop(0)
			name = ":".join(parts)
			location = {"name": name.strip(), "tag": "event", "subtag": "event"}
			_append_place(last, location, retlines)
		elif re.match("H1:.*", line.strip()):
			parts = line.strip().split(":")
			symbol = parts.pop(0)
			name = ":".join(parts)
			location = {"name": name.strip(), "tag": "event", "subtag": "h1"}
			_append_place(last, location, retlines)
		elif re.match("H2:.*", line.strip()):
			parts = line.strip().split(":")
			symbol = parts.pop(0)
			name = ":".join(parts)
			location = {"name": name.strip(), "tag": "event", "subtag": "h2"}
			_append_place(last, location, retlines)
		elif re.match("NPC:.*", line.strip()) and line.isupper():
			parts = line.strip().split(":")
			symbol = parts.pop(0)
			name = ":".join(parts)
			location = {"name": name.strip(), "tag": "npc"}
			_append_place(last, location, retlines)
		elif re.match("ROUND [0-9]+:.*", line.strip()) and line.isupper():
			parts = line.strip().split(":")
			symbol = parts.pop(0)
			name = ":".join(parts)
			location = {"symbol": symbol, "name": name.strip(), "tag": "event", "subtag": "round"}
			_append_place(last, location, retlines)
		elif re.match("TEMLATE:.*", line.strip()) and line.isupper():
			parts = line.strip().split(":")
			symbol = parts.pop(0)
			name = ":".join(parts)
			location = {"symbol": symbol, "name": name.strip(), "tag": "template"}
			_append_place(last, location, retlines)
		elif re.match("PART [A-Z]*: .*", line.strip()) and line.isupper():
			parts = line.strip().split(":")
			symbol = parts.pop(0)
			name = ":".join(parts)
			location = {"symbol": symbol, "name": name.strip(), "tag": "part"}
			_append_place(last, location, retlines)
		elif re.match(".*: .*", line.strip()) and line.isupper():
			parts = line.strip().split(":")
			symbol = parts.pop(0)
			name = ":".join(parts)
			location = {"symbol": symbol, "name": name.strip(), "tag": "part"}
			_append_place(last, location, retlines)
		else:
			retlines.append(line)
	return retlines

def _append_place(last, line, retlines):
	linetag= line["tag"]
	_pull_cr(line)
	line["name"] = cap_name(line["name"])
	if last.get(linetag) != line:
		retlines.append("%s\n" % json.dumps(line))
	last[linetag] = line

def _pull_cr(location):
	match = re.match("(.*) \(CR ([0-9/]+)\)", location["name"])
	if match:
		location["name"] = match.groups()[0]
		location["cr"] = match.groups()[1]

def xp_filter(lines):
	retlines = []
	while len(lines) > 0:
		line = lines.pop(0)
		if line.strip() == "XP":
			xplines = [line.strip()]
			while _is_xp_line(lines[0]):
				innerline = lines.pop(0)
				if not innerline.strip() == "":
					xplines.append(innerline.strip())
			statblock = dict(zip(xplines[0::2], xplines[1::2]))
			statblock["tag"] = "statblock"
			_find_name(retlines, statblock)
			_find_book(lines, statblock)
			retlines.append("%s\n" %json.dumps(statblock))
		elif re.match("XP [0-9,]+ .*", line.strip()) or re.match("XP [0-9,]+", line.strip()):
			parts = line.split()
			parts.pop(0)
			statblock = {"xp": " ".join(parts), "tag": "statblock"}
			while _is_xp_line(lines[0]):
				innerline = lines.pop(0)
				if not innerline.strip() == "":
					parts = line.split()
					title = parts.pop(0)
					statblock[title] = " ".join(parts)
			_find_name(retlines, statblock)
			_find_book(lines, statblock)
			while _is_xp_line(retlines[-1]):
				innerline = retlines.pop()
				if not innerline.strip() == "":
					parts = line.split()
					title = parts.pop(0)
					statblock[title] = " ".join(parts)
			retlines.append("%s\n" %json.dumps(statblock))
		else:
			retlines.append(line)
	return retlines

def _find_book(lines, statblock):
	while lines[0].strip() == "":
		lines.pop(0)
	if re.match("\(.*\d\)", lines[0].strip()):
		book = lines.pop(0).strip()
		statblock['book'] = book[1:-2]

def _find_name(retlines, statblock):
	while retlines[-1].strip() == "":
		retlines.pop()
	if re.match("\(.*\d\)", retlines[-1].strip()):
		book = retlines.pop().strip()
		statblock['book'] = book[1:-2]
		_find_name(retlines, statblock)
	else:
		statblock['name'] = cap_name(retlines.pop().strip())

def _is_xp_line(line):
	if line.strip() == "":
		return True
	if line.strip() in ["XP", "CR", "HP", "MR"]:
		return True
	for c in ["XP", "CR", "HP", "MR"]:
		if line.startswith(c):
			return True
	if re.match("^\d.*", line):
		return True
	return False

def title_filter(lines):
	retlines = []
	while len(lines) > 0:
		line = lines.pop(0)
		if line.strip() in ["SPECIAL ABILITIES", "DEFENSE", "OFFENSE", "TACTICS", "STATISTICS", "EFFECTS", "ECOLOGY", "Ecology", "Description", "HABITAT & SOCIETY"]:
			line = "%s\n" % json.dumps(
					{"tag": "field1", "name": line.strip().lower()})
		line = _append_field_with_results_colon(line, "Details", retlines, False)
		line = _append_field_with_results_colon(line, "TREASURE", retlines, False)
		line = _append_field_with_results_colon(line, "Treasure", retlines, False)
		line = _append_field_with_results_colon(line, "DEVELOPMENT", retlines, False)
		line = _append_field_with_results_colon(line, "Development", retlines, False)
		line = _append_field_with_results_colon(line, "STORY AWARD", retlines, False)
		line = _append_field_with_results_colon(line, "Story Award", retlines, False)
		line = _append_field_with_results_colon(line, "CREATURE", retlines, False)
		line = _append_field_with_results_colon(line, "Creature", retlines, False)
		line = _append_field_with_results_colon(line, "CREATURES", retlines, False)
		line = _append_field_with_results_colon(line, "Creatures", retlines, False)
		line = _append_field_with_results_colon(line, "HAUNT", retlines, False)
		line = _append_field_with_results_colon(line, "Haunt", retlines, False)
		line = _append_field_with_results_colon(line, "TRAP", retlines, False)
		line = _append_field_with_results_colon(line, "Trap", retlines, False)
		line = _append_field_with_results_colon(line, "Hazard", retlines, False)

		if re.match("^[LNC]?[GNE] .*", line):
			retlines.append("%s\n" % json.dumps({
				"tag": "field2", "name": "alignment", "statblock_required": True}))
		line = _append_field_with_new_header(
				line, "Init ", retlines, "senses")
		line = _append_field_with_new_header(
				line, "Aura ", retlines, "aura")

		# Defense
		line = _append_field_with_results(line, "AC", retlines)
		line = _append_field_with_results(line, "CR", retlines)
		line = _append_field_with_results(line, "hp", retlines)
		line = _append_field_with_new_header(
				line, "Fort ", retlines, "saves")
		line = _append_field_with_results(line, "Weaknesses", retlines)
		line = _append_field_with_new_header(
				line, "Defensive Abilities ", retlines, "defenses")
		line = _append_field_with_new_header(
				line, "DR ", retlines, "defenses")
		line = _append_field_with_new_header(
				line, "Immune ", retlines, "defenses")
		line = _append_field_with_new_header(
				line, "Resist ", retlines, "defenses")
		line = _append_field_with_new_header(
				line, "SR ", retlines, "defenses")

		# Offense
		line = _append_field_with_results(line, "Speed", retlines)
		line = _append_field_with_results(line, "Melee", retlines)
		line = _append_field_with_results(line, "Ranged", retlines)
		line = _append_field_with_results(line, "Space", retlines)
		line = _append_field_with_results(line, "Special Attacks", retlines)

		if line.find("Spell-Like Abilities") > -1:
			testline = line.strip()
			sla_type = testline[0:testline.find("Spell-Like Abilities")+20]
			line = _append_field_with_results(line, sla_type, retlines)

		if line.find("Spells Known") > -1:
			testline = line.strip()
			sla_type = testline[0:testline.find("Spells Known")+12]
			line = _append_field_with_results(line, sla_type, retlines)
		line = _append_field_with_results(line, "Spells Prepared", retlines)
		if re.match("^[A-Za-z]* Spells Prepared .*", line):
			parts = line.split("Spells Prepared")
			classname = parts.pop(0).strip()
			retlines.append("%s\n" % json.dumps({
				"tag": "field2", "statblock_required": True,
				"name": "%s spells prepared" % classname.lower()}))
			line = " ".join(parts).strip()

		# Tactics
		line = _append_field_with_results(line, "Before Combat", retlines)
		line = _append_field_with_results(line, "During Combat", retlines)
		line = _append_field_with_results(line, "Morale", retlines)

		# Statistics
		line = _append_field_with_results(line, "Base Statistics", retlines)
		line = _append_field_with_new_header(
				line, "Str ", retlines, "attributes")
		line = _append_field_with_new_header(
				line, "Base Atk", retlines, "attack")
		line = _append_field_with_results(line, "Feats", retlines)
		line = _append_field_with_results(line, "Skills", retlines)
		line = _append_field_with_results(line, "Languages", retlines)
		line = _append_field_with_results(line, "SQ", retlines)

		line = _append_field_with_results(line, "Combat Gear", retlines)
		line = _append_field_with_results(line, "Combat gear", retlines)
		line = _append_field_with_results(line, "Other Gear", retlines)
		line = _append_semifield_with_results(line, "Other Gear", retlines)

		line = _append_field_with_results(line, "Gear", retlines)
		line = _append_field_with_results(line, "Effect", retlines)
		line = _append_field_with_results(line, "Notice", retlines)

		line = _append_field_with_results(line, "Trigger", retlines)
		line = _append_field_with_results(line, "Type", retlines)
		retlines.append(line)
	return retlines

def _append_field_with_new_header(line, signal, retlines, fieldname, required=True):
	if line.startswith(signal):
		retlines.append("%s\n" % json.dumps({
			"tag": "field2", "name": fieldname, "statblock_required": required}))
	return line

def _append_field_with_results(line, signal, retlines, required=True):
	if line.startswith(signal + " "):
		retlines.append("%s\n" % json.dumps(
			{"tag": "field2", "name": signal.lower(), "statblock_required": required}))
		line = line[len(signal):].strip() + "\n"
	return line

def _append_semifield_with_results(line, signal, retlines, required=True):
	if line.find("; " + signal) > -1:
		parts = line.strip().split("; " + signal)
		retlines.append("%s\n" % parts.pop(0))
		retlines.append("%s\n" % json.dumps(
			{"tag": "field2", "name": signal.lower(), "statblock_required": required}))
		line = ";".join(parts) + "\n"
	return line

def _append_field_with_results_colon(line, signal, retlines, required=True):
	if line.startswith(signal + ":"):
		retlines.append("%s\n" % json.dumps(
			{"tag": "details", "name": signal.lower(), "statblock_required": required}))
		line = line[len(signal)+1:].strip() + "\n"
	return line

def int_filter(lines):
	retlines = []
	while len(lines) > 0:
		line = lines.pop(0)
		if line.strip().isdigit():
			while retlines[-1].strip() == "":
				retlines.pop()
			while lines[0].strip() == "":
				lines.pop(0)
				if len(lines) == 0:
					return retlines
		else:
			retlines.append(line)
	return retlines

def pageend_filter(lines):
	retlines = []
	while len(lines) > 0:
		line = lines.pop(0)
		if line.strip() == "|PAGEEND|":
			for i in range(len(lines)):
				line = lines[i].strip()
				if line == "":
					continue
				if not line.isupper():
					break
				if line == "|PAGEEND|":
					lines = lines[i:]
					break
		else:
			retlines.append(line)
	return retlines

def collapse_filter(lines):
	retlines = []
	last = {}
	current = None
	while len(lines) > 0:
		line = lines.pop(0)
		if line.startswith("{"):
			data = json.loads(line)
			tag = data["tag"]
			last[tag] = data
			if current:
				if tag in ["event", "statblock", "part", "details"]:
					current = _collapse_subrecords(current)
					retlines.append("%s\n" % json.dumps(current))
					if tag in ["event", "part"]:
						if data.has_key("lines"):
							data = _collapse_subrecords(data)
					if tag not in ["statblock"]:
						retlines.append("%s\n" % json.dumps(data))
					current = None
				else:
					current["lines"].append(data)
			if tag == "statblock":
				current = data
				current["lines"] = []
				current["context"] = {
						"part": last.get('part'),
						"event": last.get('event')}
		elif current:
			if line.strip() != "":
				current["lines"].append(line)
		else:
			retlines.append(line)
	return retlines

def _collapse_subrecords(data):
	lines = data["lines"]
	del data["lines"]
	source = data.setdefault("source", {"lines": []})
	field1 = None
	field2 = None
	for field in lines:
		if type(field) == dict:
			tag = field["tag"]
			if tag == "field1":
				field1 = field["name"]
				field2 = None
			elif tag == "field2":
				field2 = field["name"]
			else:
				raise Exception("I don't recognize a tag of %s" % field)
		else:
			field = unicode_filter(field)
			if field1 == None and field2 == None:
				source["lines"].append(field)
			elif field1 and field2 == None:
				f = source.setdefault(field1, {})
				l = f.setdefault("lines", [])
				l.append(field)
			elif field2 and field1 == None:
				f = source.setdefault(field2, {})
				l = f.setdefault("lines", [])
				l.append(field)
			elif field1 and field2:
				f = source.setdefault(field1, {})
				f2 = f.setdefault(field2, {})
				l = f2.setdefault("lines", [])
				l.append(field)
	return data

def unicode_filter(line):
	line = line.replace(u"\u2013".encode('utf-8'), "-")
	line = line.replace(u"\u2014".encode('utf-8'), "-")
	return line

