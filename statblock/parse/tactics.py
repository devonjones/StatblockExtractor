from statblock.parse.utils import yield_statblocks

def parse_tactics(lines):
	retlines = []
	for statblock in yield_statblocks(lines, retlines):
		source = statblock.setdefault("source", {})
		tactics_source = source.setdefault("tactics", {})
		tactics = statblock.setdefault("tactics", {})
		for key in tactics_source:
			_handle_text(tactics, key, tactics_source[key])
		del source["tactics"]
		if len(tactics) == 0:
			del statblock["tactics"]
	return retlines

def _handle_text(section, token, data):
	lines = data['lines']
	content = " ".join([line.strip() for line in lines])
	section[token] = content
