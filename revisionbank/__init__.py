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

from flask_pymongo import PyMongo

import revisionbank.page

app = flask.Flask(__name__)
mongo = PyMongo(app)

@app.route('/')
def index():
	return flask.render_template('index.html')

@app.route('/page/<path:page_name>')
def page_view(page_name):
	page_json = mongo.db.pages.find_one({'name': page_name})
	if page_json is None:
		page = revisionbank.page.Page404(name=page_name)
	else:
		page = revisionbank.page.PageMarkdown(**page_json)
	
	return flask.render_template('page.html', page=page)

@app.route('/page/<path:page_name>/edit')
def page_edit(page_name):
	page_json = mongo.db.pages.find_one({'name': page_name})
	if page_json is None:
		page = revisionbank.page.PageMarkdown(name=page_name)
	else:
		page = revisionbank.page.PageMarkdown(**page_json)
	
	return flask.render_template('page_edit.html', page=page)
