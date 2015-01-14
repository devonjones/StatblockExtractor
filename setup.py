#!/usr/bin/env python
import glob
import os.path
import re
from setuptools import Command, find_packages, setup

class PyTest(Command):
	user_options = []
	def initialize_options(self):
		pass
	def finalize_options(self):
		pass
	def run(self):
		import sys, subprocess
		errno = subprocess.call(["./test.sh"])
		raise SystemExit(errno)

def parse_requirements(file_name):
	"""Taken from http://cburgmer.posterous.com/pip-requirementstxt-and-setuppy"""
	requirements = []
	path = os.path.join(os.path.dirname(__file__), "config", file_name)
	if os.path.exists(path):
		for line in open(path, "r"):
			line = line.strip()
			# comments and blank lines
			if re.match(r"(^#)|(^$)", line):
				continue
			requirements.append(line)

	return requirements

setup(
	name = "statblock",
	version = "0.1",
	url = "http://github.com/devonjones/statblock",
	author = "Devon Jones",
	author_email = "devon.jones@gmail.com",
	scripts = [
		'bin/statblock'
	],
	packages = find_packages(),
#	cmdclass = {"test": PyTest},
	package_data = {"config": ["requirements.txt"]},
	install_requires = parse_requirements("requirements.txt"),
	tests_require = parse_requirements("requirements.txt"),
	description = "Program to pull tatblocks out of pdfs.",
	long_description = "\n" + open("README.md").read(),
)
