import json

def required_check(lines):
	retlines = []
	for line in lines:
		if line.startswith("{"):
			data = json.loads(line)
			tag = data.get("tag")
			if tag in ["field1", "field2"]:
				if tag.get("statblock_required"):
					sys.stderr.write("Statblock data found outside statblocker: %s\n" % json.dumps(data, indent=True))
					sys.exit(1)
	return retlines

def format_check(lines):
	retlines = []
	while len(lines) > 0:
		line = lines.pop(0)
		if line.startswith("{"):
			data = json.loads(line)
			retlines.append("%s\n" % json.dumps(data, indent=2))
		else:
			retlines.append(line)
	return retlines
