import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, render_template, flash, abort
from contextlib import closing
import forms

#Create the application
app = Flask(__name__)
app.config.update(dict(
	DATABASE=os.path.join(app.root_path, 'pprwork.db'),
	DEBUG=True,
	SECRET_KEY="development key",
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

def connect_db():
	return sqlite3.connect(app.config['DATABASE'])

def init_db():
	with closing(connect_db()) as db:
		with app.open_resource("schema.sql", mode="r") as f:
			db.cursor().executescript(f.read())
		db.commit()

@app.before_request
def before_request():
	g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
	db = getattr(g, 'db', None)
	if db is not None:
		db.close()

def createFriendship(friendid):
	userid = getCurrentUserId()
	g.db.execute('insert into friends (frienderId, friendedId) values (?, ?)', [userid, friendid])
	g.db.commit()

def getFriends(userid):
	stack = []
	query1 = g.db.execute('select friendedId from friends where frienderId = ?', (userid,))
	query2 = g.db.execute('select frienderId from friends where friendedId = ?', (userid,))

	for row in query1:
		stack.append(row[0])
	for row in query2:
		stack.append(row[0])
	return stack

def getUserId(username):
	return g.db.execute('select id from users where username = ?', (username,)).fetchone()[0]

def getCurrentUserId():
	return getUserId(session['username'])

@app.route('/')
def show_entries():
	cur = g.db.execute('select title, text from entries order by id desc')
	entries = [dict(title = row[0], text = row[1]) for row in cur.fetchall()]
	return render_template('show_entries.html', entries=entries)

@app.route('/add', methods=['POST'])
def add_entry():
	if not session.get('logged_in'):
		abort(401)
	g.db.execute('insert into entries (title, text) values (?, ?)',
		[request.form['title'], request.form['text']])
	g.db.commit()
	flash('New entry was successfully posted')
	return redirect(url_for('show_entries'))

@app.route('/login', methods=['GET', 'POST'])
def login():
	error = None
	form = forms.LoginForm(request.form)
	if request.method == 'POST' and form.validate():
		if g.db.execute('select exists(select 1 from users where username = ? limit 1)', (form.username.data,)) is 0:
			error = 'Invalid username'
		elif g.db.execute('select password from users where username = ?', (form.username.data,)).fetchone()[0] != form.password.data:
			error = 'Invalid password'
		else:
			session['logged_in'] = True
			session['username'] = form.username.data
			flash('You were logged in')
			return redirect(url_for('show_entries'))
	return render_template('login.html', form=form, error=error)

@app.route('/logout')
def logout():
	session.pop('logged_in', None)
	session.pop('username', None)
	flash('You were logged out')
	return redirect(url_for('show_entries'))

@app.route('/register', methods=['GET', 'POST'])
def register():
	error = None
	form = forms.RegistrationForm(request.form)
	if request.method == 'POST' and form.validate():
		cur = g.db.execute('select * from users where username = ?', (form.username.data,)).fetchone()
		if cur is not None:
			error = "Username already taken"
		elif form.username.data == "searchbox":
			error = "Invalid username"
		else:
			g.db.execute('insert into users (username, firstname, lastname, password, email) values (?, ?, ?, ?, ?)',
				[form.username.data, form.firstname.data, form.lastname.data, form.password.data, form.email.data])
			g.db.commit()
			flash('Your account has been registered')
			return redirect(url_for('login'))
	return render_template('register.html', form=form, error=error)

@app.route('/search', methods=['GET', 'POST'])
def search():
	userentries = None
	f = request.form
	for key in f.keys():
		for value in f.getlist(key):
			print key,":",value
	if request.form['searchbox'] != None:
		print('going through')
		query1 = g.db.execute("select username, firstname, lastname from users where username like ?", ('%'+request.form['searchbox']+'%',))
		userentries = [dict(username = row[0], firstname = row[1], lastname = row[2]) for row in query1.fetchall()]
	elif request.form['action'] != None:
		print('hello')
		#return redirect(url_for('show_entries.html'))
	print('end')
	return render_template('search.html', userentries=userentries)

@app.route('/invite', methods=['GET', 'POST'])
def invite():
	form = forms.InviteFriendForm(request.form)
	if request.method == 'POST' and form.validate():
		#Send the email via flask-mail
		flash('Invitation sent!')
	return render_template('invitefriends.html', form=form)

@app.route('/sets/add', methods=['GET', 'POST'])
def addsets():
	error = None
	form = forms.SetForm(request.form)
	if request.method == 'POST' and form.validate():
		cur = g.db.execute('select * from sets where name = ?', (form.name.data,)).fetchone()
		if cur is None:
			g.db.execute('insert into sets (creatorId, isPublic, categorytype, name) values (?, ?, ?, ?)',
				[getCurrentUserId(), form.public.data, form.category.data, form.name.data])
			g.db.commit()
			flash('Your new set has been created')
			cur = g.db.execute('select id from sets where name = ?', (form.name.data,)).fetchone[0]
			redirect('url_for(addquestions)' + '/' + cur)
		else:
			error = "This set's name is already being used. Choose a different name."
	return render_template('addset.html', form=form, error=error)

@app.route('/questions/add/<int:set_id>', methods=['GET', 'POST'])
def addquestions(set_id):
	query = g.db.execute('select id, name from sets where creatorId = ?', (getCurrentUserId,))
	queryentries = [dict(id = row[0], name = row[1]) for row in query1.fetchall()]
	default = None
	for entries in queryentries:
		if set_id == entries.id:
			default = set_id
			continue
	if default is not None:
		form = forms.QuestionForm(request.form, setbox=default)
	else:
		form = forms.QuestionForm(request.form)
	form.setbox.choices = [(q.id, q.name) for q in queryentries]
	if request.method == 'POST' and form.validate():
		pass
	return render_template('addquestion.html', form=form)

if __name__ == "__main__":
	app.run()