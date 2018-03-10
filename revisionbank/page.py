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

from datetime import datetime
import flask
import jinja2
import mwparserfromhell as mw
import pytz
import re

class MongoObject:
	@classmethod
	def from_json(cls, json_obj):
		return cls(**json_obj)

class BasePage(MongoObject):
	def __init__(self, name=None):
		self.name = name
	
	@property
	def pretty_name(self):
		return self.name.split('/')[-1]
	
	def to_json(self):
		return {'name': self.name}

class Page404(BasePage):
	@property
	def revisions(self):
		return [Revision404(self)]

class Page(BasePage):
	def __init__(self, _id=None, revisions=None, **kwargs):
		super().__init__(**kwargs)
		if revisions is None:
			revisions = []
		self.revisions = revisions
	
	def to_json(self):
		json_obj = super().to_json()
		json_obj.update({'revisions': [r.to_json() for r in self.revisions]})
		return json_obj
	
	@classmethod
	def from_json(cls, json_obj):
		obj = Page(**json_obj)
		obj.revisions = [RevisionMarkdown.from_json(r, obj) for r in obj.revisions]
		return obj

class Revision(MongoObject):
	def __init__(self, page=None, creator=None, creation_date=None, reason=None):
		self.page = page
		
		self.creator = creator
		self.creation_date = creation_date
		self.reason = reason
	
	def to_json(self):
		return {'creator': self.creator.to_json(), 'creation_date': self.creation_date.strftime('%Y-%m-%dT%H:%M:%SZ'), 'reason': self.reason}
	
	@classmethod
	def from_json(cls, json_obj, page=None):
		import revisionbank.user
		
		obj = cls(**json_obj)
		obj.page = page
		obj.creator = revisionbank.user.GoogleUser.from_json(obj.creator)
		obj.creation_date = pytz.utc.localize(datetime.strptime(json_obj['creation_date'], '%Y-%m-%dT%H:%M:%SZ'))
		return obj

class Revision404(Revision):
	def render_content(self):
		return jinja2.Markup(flask.render_template('page_404.html', page=self.page))
	
	@property
	def content(self):
		return ''

def markup_delimtag(pattern, tag1, tag2, markup):
	markup = markup.replace(jinja2.escape(pattern), jinja2.Markup('\ue000'))
	markup = markup_resub(r'\ue000(.*?)\ue000', r'{0}\1{1}'.format(tag1, tag2), markup)
	markup = markup.replace(jinja2.Markup('\ue000'), jinja2.escape(pattern))
	return markup

def markup_resub(pattern, repl, markup):
	return jinja2.Markup(re.sub(pattern, repl, str(markup)))

class RevisionMarkdown(Revision):
	def __init__(self, content=None, **kwargs):
		super().__init__(**kwargs)
		self.content = content
	
	def render_node(self, node):
		if isinstance(node, mw.nodes.text.Text):
			markup = jinja2.escape(node.value)
			markup = markup_delimtag('***', '<b><i>', '</i></b>', markup)
			markup = markup_delimtag('**', '<b>', '</b>', markup)
			markup = markup_delimtag('*', '<i>', '</i>', markup)
		elif isinstance(node, mw.wikicode.Wikicode):
			markup = jinja2.Markup()
			for subnode in node.ifilter():
				markup += self.render_node(subnode)
		return markup
	
	def render_content(self):
		wikitext = mw.parse(self.content)
		markup = self.render_node(wikitext)
		return markup
	
	def to_json(self):
		json_obj = super().to_json()
		json_obj.update({'content': self.content})
		return json_obj
