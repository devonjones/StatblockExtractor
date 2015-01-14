import re

def filter_none(line):
	if line:
		return line
	else:
		return "-"

def filter_mdash(line):
	return line.replace("&mdash", "-")

def cap_name(name):
	return " ".join([field.capitalize() for field in name.split(" ")])

def split(string, char=","):
	r = re.compile(r'(?:[^%s(]|\([^)]*\))+' % char)
	return r.findall(string)

def filter_path_element(path_element):
	path_element = path_element.replace("\u2019".encode('utf-8'), "")
	path_element = path_element.replace(" ", "_")
	path_element = path_element.replace(",", "")
	path_element = path_element.replace("(", "")
	path_element = path_element.replace(")", "")
	path_element = path_element.replace("/", "-")
	path_element = path_element.lower()
	return path_element

