from flask import Flask, render_template, request, session, redirect, flash
from flask_bcrypt import Bcrypt
from mysqlconnection import connectToMySQL
import re
import copy
from datetime import datetime, timedelta

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9.+_-]+\.[a-zA-z]+$')

app=Flask(__name__)
app.secret_key = "ThisIsASecret"
bcrypt = Bcrypt(app)     # we are creating an object called bcrypt, 
                         # which is made by invoking the function Bcrypt with our app as an argument

@app.template_filter('duration_elapsed')
def timesince(dt, default="just now"):

    now = datetime.now()
    diff = now - dt
    
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)
    return default

@app.route("/")

def index():

	if 'loggedin' not in session:
		session["first_name"] = ""
		session["last_name"] = ""
		session["email"] = ""
		session["userid"] = ""
		session["loggedin"] = False
	elif session["loggedin"] == True:
		session.clear()

	return render_template ("index.html")

@app.route("/register", methods = ["POST"])

def logincheck():


	#first name errors
	if len(request.form['first_name']) < 1:
		flash("This field is required", "flashfirstname")
	elif len(request.form['first_name']) < 2:
		flash("First name needs to be longer than two characters, and contain only text.","flashfirstname")
	elif request.form['first_name'].isalpha() == False:
		flash("First name cannot contain numbers", "flashfirstname")

	#last name errors
	if len(request.form['last_name']) < 1:
		flash("This field is required", "flashlastname")
	elif len(request.form['last_name']) < 2:
		flash("Last name needs to be longer than two characters, and contain only text.", "flashlastname")
	elif request.form['last_name'].isalpha() == False:
		flash("Last name cannot contain numbers", "flashlastname")

	#email errors
	if len(request.form['email']) < 1:
		flash("This field is required", "flashemail")
	elif not EMAIL_REGEX.match(request.form['email']):
		flash("Invalid Email Address", "flashemail")

	#check e-mail against database and returns count
	mysql = connectToMySQL("mydb")
	query = "select idUsers,emails from users where emails = %(emails)s;"
	data = {"emails":request.form["email"]}
	emailcheck = mysql.query_db(query,data)

	#password errors
	if len(request.form['password']) < 1:
		flash("This field is required", "flashpassword")
	elif len(request.form['password']) < 8:
		flash("Password name needs to be longer than eight characters", "flashpassword")

	#confirm password errors
	if len(request.form['confirmpassword']) < 1:
		flash("This field is required", "flashconfirmpassword")
	elif len(request.form['confirmpassword']) < 8:
		flash("Password name needs to be longer than eight characters", "flashconfirmpassword")
	elif request.form['password'] != request.form['confirmpassword']:
		flash("The passwords do not match.","flashpassword")

	# if emailcheck: <- checks if you get a result or not
	#if count of e-mails is less than 1 insert into table
	if emailcheck:
		flash("This email is already registered.", "flashemail")

	if '_flashes' in session.keys():

		session["email"] = request.form["email"]
		session["first_name"] = request.form["first_name"]
		session["last_name"] = request.form["last_name"]
		session["loggedin"] = False

		return redirect("/")
	else:
		session["email"] = request.form["email"]
		session["first_name"] = request.form["first_name"]
		session["last_name"] = request.form["last_name"]
		session["loggedin"] = True

		pw_hash = bcrypt.generate_password_hash(request.form['password'])

		mysql = connectToMySQL('mydb')
		query2 = "insert into users (idUsers,first_name,last_name,emails,password,date_created,last_updated) values (idUsers,%(first_name)s, %(last_name)s,%(emails)s,%(password_hash)s,now(),now())"
		data2 = {
		"first_name": request.form["first_name"],
		"last_name": request.form["last_name"],
		"emails":request.form["email"],
		"password_hash": pw_hash
		}
		insertemail = mysql.query_db(query2,data2)

		mysql = connectToMySQL("mydb")
		query = "select idUsers,emails from users where emails = %(emails)s;"
		data = {"emails":request.form["email"]}
		emailcheck = mysql.query_db(query,data)
		session['userid'] = emailcheck[0]['idUsers']

		flash("You've successly been registered.", "flashsuccess")
		return redirect("/success")

@app.route("/login", methods = ["POST"])

def login():

	mysql = connectToMySQL("mydb")
	query = "SELECT * FROM users WHERE emails = %(emails)s;"
	data = { 
		"emails" : request.form["email"]
	}
	result = mysql.query_db(query, data)
	# print (result)

	if result:
		if bcrypt.check_password_hash(result[0]['password'], request.form['password']):
		# if we get True after checking the password, we may put the user id in session
			session['userid'] = result[0]['idUsers']
			session["first_name"] = result[0]["first_name"]
			session["last_name"] = result[0]["last_name"]
			session["loggedin"] = True
			return redirect('/thewall')
	flash("This email login and password combination does not exist.","flashlogin")
	return redirect("/")

@app.route("/success")

def success():

	# print(session["userid"])

	if session["userid"] == "":
		flash("You must be logged in to enter this website.", "flashlogout")
		return redirect ("/")
	else:
		return redirect ("/thewall")

@app.route("/thewall")

def thewall():

	#shows all quotes and the users who sent them
	mysql = connectToMySQL("mydb")
	query = "select * from quotes inner join users on users.idUsers = quotes.user_id order by date_added desc"
	quotes = mysql.query_db(query)

	#shows all likes made on each message
	mysql = connectToMySQL("mydb")
	query = "select quote_id, count(*) from likes group by quote_id"
	likes = mysql.query_db(query)

	return render_template("thewall.html",quotes = quotes,likes = likes)

@app.route('/edit/<id>')

def edit(id):

	mysql = connectToMySQL("mydb")
	query = "select * from users where idUsers = %(user_id)s"
	data = {
		'user_id':id
		}
	viewuser = mysql.query_db(query,data)
	return render_template('/edit.html',viewuser = viewuser)

@app.route('/editprocess', methods = ["POST"])

def editprocess():

	#first name errors
	if len(request.form['firstname']) < 1:
		flash("This field is required", "description")
	elif len(request.form['firstname']) < 2:
		flash("First name needs to be longer than two characters, and contain only text.","description")
	elif request.form['firstname'].isalpha() == False:
		flash("First name cannot contain numbers", "description")

	#last name errors
	if len(request.form['lastname']) < 1:
		flash("This field is required", "description")
	elif len(request.form['lastname']) < 2:
		flash("Last name needs to be longer than two characters, and contain only text.", "description")
	elif request.form['lastname'].isalpha() == False:
		flash("Last name cannot contain numbers", "description")

	#email errors
	if len(request.form['email']) < 1:
		flash("This field is required", "description")
	elif not EMAIL_REGEX.match(request.form['email']):
		flash("Invalid Email Address", "description")

	#check e-mail against database and returns count
	mysql = connectToMySQL("mydb")
	query = "select idUsers,emails from users where emails = %(emails)s;"
	data = {"emails":request.form["email"]}
	emailcheck = mysql.query_db(query,data)

	if emailcheck:
		flash("This email is already registered.", "description")
	if '_flashes' in session.keys():
		return redirect('/edit/'+str(session['userid']))
	else:
		mysql = connectToMySQL("mydb")
		query = "UPDATE users SET first_name = %(firstname)s,last_name = %(lastname)s, emails = %(email)s, last_updated = now() where idUsers = %(userid)s"
		data = { 
			"userid" : request.form['userid'],		
			"firstname":request.form['firstname'],
			"lastname":request.form['lastname'],
			"email": request.form['email']
			}
		updateprofile = mysql.query_db(query,data)
		return redirect('/thewall')

@app.route("/addquote", methods = ["POST"])

def addquote():

	if len(request.form['quote']) < 10:
		flash("Quote needs to be longer than 10 characters.", "description")

	if len(request.form['author']) < 3:
		flash("Author needs to be longer than 3 characters.", "description")

	if '_flashes' in session.keys():
		return redirect("/thewall")
	else:
		mysql = connectToMySQL('mydb')
		query = "INSERT INTO quotes (quote,author,user_id,date_added,date_updated) VALUES (%(quote)s,%(author)s,%(userid)s,now(),now())"

		data = {
			'quote': request.form["quote"],
			'author': request.form['author'],
			'userid': session['userid']
			}
		addquote = mysql.query_db(query,data)
		return redirect("/thewall")

@app.route('/like', methods = ["POST"])

def like():

	mysql = connectToMySQL("mydb")
	query = "SELECT * from likes where quote_id = %(quote_id)s and user_id = %(user_id)s"
	data = {
		'quote_id': request.form['idquote'],
		'user_id' : session['userid']
		}
	likecheck = mysql.query_db(query,data)

	if likecheck:
		flash("You can only like a quote once!", "flashlike")
	if '_flashes' in session.keys():
		return redirect('/thewall')
	else:
		mysql = connectToMySQL('mydb')
		query = "INSERT INTO likes (quote_id,date_added,user_id) VALUES (%(quote_id)s,now(),%(userid)s)"
		data = {
			'quote_id': request.form["idquote"],
			'userid': session['userid']
			}
		likequote = mysql.query_db(query,data)
		return redirect('/thewall')

@app.route('/view/<id>')

def view(id):

	mysql = connectToMySQL("mydb")
	query = "select * from quotes inner join users on users.idUsers = quotes.user_id where quotes.user_id = %(user_id)s order by date_added desc"
	data = {
		'user_id':id
		}
	views = mysql.query_db(query,data)
	return render_template('review.html', views = views)

@app.route('/delete/<id>')

def delete(id):

    mysql = connectToMySQL('mydb')
    query = ("DELETE FROM quotes WHERE (idquote = %(id)s and user_id = %(userid)s)")
    data = {
        'id' : id,
        'userid':session['userid']
    }

    deletequote = mysql.query_db(query,data)

    return redirect('/thewall')

@app.route("/logout")

def logout():

	session.clear()

	flash("You have been logged out.","flashlogout")
	return redirect ("/")

if __name__ == "__main__":
	app.run(debug=True)