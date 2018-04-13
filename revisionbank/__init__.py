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

from flask_oauthlib.client import OAuth
from flask_pymongo import PyMongo

import revisionbank.page
import revisionbank.user

from datetime import datetime
import functools
import hashlib
import os
import pytz

app = flask.Flask(__name__)

if 'REVBANK_SETTINGS' in os.environ:
	app.config.from_envvar('REVBANK_SETTINGS')

mongo = PyMongo(app)

@app.route('/')
def index():
	page_json = mongo.db.pages.find_one({'name': 'Home'})
	if page_json is None:
		page = revisionbank.page.Page404(name=page_name)
	else:
		page = revisionbank.page.Page.from_json(page_json)
	
	revision = page.revisions[int(flask.request.args.get('revision', 0)) - 1]
	
	return flask.render_template('index.html', page=page, revision=revision)

def sanitise_page_name(viewfunc):
	@functools.wraps(viewfunc)
	def wrapper(page_name):
		if page_name != page_name.strip():
			return flask.redirect(flask.url_for(viewfunc, page_name=page_name.strip()))
		if page_name.endswith('/'):
			return flask.redirect(flask.url_for(viewfunc, page_name=page_name[:-1]))
		
		return viewfunc(page_name)
	return wrapper

@app.route('/page/<path:page_name>')
@sanitise_page_name
def page_view(page_name):
	if page_name != page_name.strip():
		return flask.redirect(flask.url_for('page_view', page_name=page_name.strip()))
	if page_name.endswith('/'):
		return flask.redirect(flask.url_for('page_view', page_name=page_name[:-1]))
	
	page_json = mongo.db.pages.find_one({'name': page_name})
	if page_json is None:
		page = revisionbank.page.Page404(name=page_name)
	else:
		page = revisionbank.page.Page.from_json(page_json)
	
	revision = page.revisions[int(flask.request.args.get('revision', 0)) - 1]
	
	return flask.render_template('page.html', page=page, revision=revision)

@app.route('/page/<path:page_name>/edit', methods=['GET', 'POST'])
@sanitise_page_name
def page_edit(page_name):
	if flask.request.method == 'GET':
		page_json = mongo.db.pages.find_one({'name': page_name})
		if page_json is None:
			page = revisionbank.page.Page(name=page_name)
		else:
			page = revisionbank.page.Page.from_json(page_json)
		
		return flask.render_template('page_edit.html', page=page)
	else:
		if 'google_user' not in flask.session:
			return flask.abort(403)
		
		page_json = mongo.db.pages.find_one({'name': page_name})
		if page_json is None:
			page = revisionbank.page.Page(name=page_name)
		else:
			page = revisionbank.page.Page.from_json(page_json)
		
		if page_name.startswith('Script:'):
			tmp = hashlib.sha256()
			tmp.update(flask.session['google_user']['email'].encode('utf-8'))
			if tmp.hexdigest() != 'd86022c789a8523589a3a2e0ed7db52e33bae0bb56ef5cd03bcb9be35783044c':
				return flask.abort(403)
			revision = revisionbank.page.RevisionScript()
		else:
			revision = revisionbank.page.RevisionMarkdown()
		
		revision.creator = current_user()
		revision.creation_date = pytz.utc.localize(datetime.utcnow())
		revision.content = flask.request.form['page-content']
		revision.reason = flask.request.form['edit-reason']
		
		page.revisions.append(revision)
		
		mongo.db.pages.replace_one({'name': page_name}, page.to_json(), upsert=True)
		
		return flask.redirect(flask.url_for('page_view', page_name=page_name))

@app.route('/page/<path:page_name>/history')
@sanitise_page_name
def page_history(page_name):
	page_json = mongo.db.pages.find_one({'name': page_name})
	if page_json is None:
		page = revisionbank.page.Page404(name=page_name)
	else:
		page = revisionbank.page.Page.from_json(page_json)
	
	return flask.render_template('page_history.html', page=page)

oauth = OAuth(app)
google = oauth.remote_app(
	'google',
	consumer_key=app.config.get('GOOGLE_ID'),
	consumer_secret=app.config.get('GOOGLE_SECRET'),
	request_token_params={
		'scope': 'email profile',
		'hd': app.config.get('GOOGLE_HD')
	},
	base_url='https://www.googleapis.com/oauth2/v1/',
	request_token_url=None,
	access_token_method='POST',
	access_token_url='https://accounts.google.com/o/oauth2/token',
	authorize_url='https://accounts.google.com/o/oauth2/auth',
)

@app.route('/auth/tmp')
def auth_tmp():
	if 'google_token' in flask.session:
		me = google.get('userinfo')
		return flask.jsonify({"data": me.data})
	return flask.redirect(flask.url_for('login'))

@app.route('/auth/login')
def login():
	return google.authorize(callback=flask.url_for('authorized', _external=True))

@app.route('/auth/logout')
def logout():
	flask.session.pop('google_token', None)
	flask.session.pop('google_user', None)
	return flask.redirect(flask.url_for('index'))

@app.route('/auth/authorized')
def authorized():
	resp = google.authorized_response()
	if resp is None:
		return 'Access denied'
	flask.session['google_token'] = (resp['access_token'], '')
	me = google.get('userinfo')
	
	if me.data['hd'] == app.config.get('GOOGLE_HD') or me.data['hd'].endswith('.' + app.config.get('GOOGLE_HD')):
		pass
	else:
		# Invalid domain
		flask.session.pop('google_token', None)
		return 'Access denied: Invalid domain'
	
	flask.session['google_user'] = me.data
	return flask.redirect(flask.url_for('index'))

@google.tokengetter
def get_google_oauth_token():
	return flask.session.get('google_token')

def current_user():
	if 'google_token' not in flask.session:
		return None
	return revisionbank.user.GoogleUser(name=flask.session['google_user']['name'], email=flask.session['google_user']['email'])
