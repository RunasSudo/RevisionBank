#   RevisionBank
#   Copyright © 2018  Yingtong Li (RunasSudo)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

import flask
import jinja2

import random

class Script:
	pass

builtin_scripts = {}
def builtin_script(name):
	def wrapper(cls):
		builtin_scripts[name] = cls
		return cls
	return wrapper

class Option:
	def __init__(self, text, value):
		self.text = text
		self.value = value

class OptionSpec:
	def __init__(self):
		self.value = 0
	
	@staticmethod
	def parse(spec):
		if len(spec) == 1:
			return OptionSpecSimple(*spec)
		return None

class OptionSpecSimple(OptionSpec):
	def __init__(self, text):
		super().__init__()
		self.text = text
		
		if self.text.startswith('*'):
			self.value = 1
			self.text = self.text[1:]
	
	def build(self):
		return [Option(self.text, self.value)]

@builtin_script('MCQ')
class MCQ(Script):
	def render(page, node):
		# Split params by line, then by |
		lines = [[y.strip() for y in x.split('|')] for x in '|'.join([str(p) for p in node.params]).strip('\n').split('\n')]
		
		# Parse parameters
		prompt = lines[0][0]
		number = int(lines[0][1]) if len(lines[0]) > 1 else 5
		optspec_strl = lines[1:]
		
		# Parse option specifications
		optspecs = [OptionSpec.parse(x) for x in optspec_strl]
		
		# Build possible options
		options = []
		for optspec in optspecs:
			options.extend(optspec.build())
		
		#options_subset = []
		## Choose a correct answer
		#options_subset.append(random.choice([opt for opt in options if opt.value >= 1]))
		## Choose n incorrect answers
		#incorrects = [opt for opt in options if opt.value < 1]
		#if len(incorrects) <= number - 1:
		#	options_subset.extend(incorrects)
		#else:
		#	options_subset.extend(random.sample(incorrects, number - 1))
		
		#return jinja2.Markup(flask.render_template('questions/mcq.html', prompt=prompt, options=options_subset))
		return jinja2.Markup(flask.render_template('questions/mcq.html', prompt=prompt, options=options))
