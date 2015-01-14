import re
from statblock.parse.utils import yield_statblocks
from statblock.parse.utils import create
from statblock.utils import cap_name

def parse_special_abilities(lines):
	retlines = []
	for statblock in yield_statblocks(lines, retlines):
		source = statblock.setdefault("source", {})
		sa_source = source.setdefault("special abilities", {})
		sa = None
		ability = {}
		sa_types = {"Ex": "Extraordinary", "Su": "Supernatural", "Sp": "Spell-Like"}
		for line in sa_source.get("lines", []):
			m = re.match("([A-Z ]*): (.*)", line.strip())
			if m:
				name = cap_name(m.groups()[0])
				description = m.groups()[1].strip()
				sa = statblock.setdefault("special_abilities", [])
				ability = create(
					"special_ability", name=name, description=description)
				sa.append(ability)
				continue

			m = re.match(u"([A-Za-z \u2019-]*) \(([SE][uxp])\) (.*)", line.strip())
			if m:
				name = cap_name(m.groups()[0])
				sa_type = m.groups()[1]
				description = m.groups()[2].strip()
				sa = statblock.setdefault("special_abilities", [])
				ability = create(
					"special_ability", name=name, description=description,
					ability_type=sa_types[sa_type], ability_type_abbrev=sa_type)
				sa.append(ability)
				continue
			ability["description"] = " ".join(
					[ability["description"], line.strip()])
		del source["special abilities"]
	return retlines
