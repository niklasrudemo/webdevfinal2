# Main file for Niklas Rudemos final project in Udacity's webdev course
# This file mainly contains the direct URL-handlers.
# Utilities are kept in the util.py file. This creates some unwanted
# issue in that
# a) a number of modules have to be imported in both files
# b) from utils is very long
# These two issues indicates that the abstractions used are imperfect,
# and that there is room for improvement in this regard.
# There is one stylesheets, in the stylesheet directory, but since the
# CSS used is very rudimentary, it is of limited importance.
# Templates are used more extensively, and a base.html is used as the
# basis for the other templates.
# 
# Naming convention: URL-handler are named on the format <Url>Page,
# i.e. SignupPage, LoginPage, etc. Otherwise, the
# conventional python naming using underscores is used. This is 
# in keeping with recommendations from PEP 8.

import datetime
import hashlib
import jinja2
import os
import pickle
import random
import re
import string
import time
import unicodedata
import webapp2
from urllib import quote
from google.appengine.ext import db
from google.appengine.api import memcache

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                                                           autoescape = False)

PAGE_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)'

############################################
############ DATABASE DEFINITIONS ##########


class PagesDB(db.Model):
	""" Class for Pages in the database. """
	url = db.StringProperty(required = True)
	subject = db.StringProperty()
	content = db.TextProperty(required = True)
	modified = db.DateTimeProperty(auto_now_add = True)
	version = db.IntegerProperty(required = True)


class UserDB(db.Model):
	""" Class for users in the database. """
	username = db.StringProperty(required = True)
	email = db.StringProperty(required = True)
	password_hash = db.StringProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)


############################################
############ UTILITY FUNCTIONS #############

def hash_str(s):
    return hashlib.md5(s).hexdigest()

def make_secure_val(s):
    return str("%s|%s" % (s, hash_str(s)))

def check_secure_val(h):
    if h:
        username = h.split('|')[0]
        if h==make_secure_val(username):
            return username
    else:
        return None

def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw):
    salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    h_string = '%s,%s' % (h, salt)
    return h_string

def is_password_invalid(password):
    if re.match(r"^[a-zA-Z0-9._]{4,}$", password)!=None:
        return False
    return True

def is_username_invalid(username):
    if re.match(r"^[a-zA-Z0-9._]{2,}$", username)!=None:
        return False
    return True

def is_email_invalid(email):
    if re.match(r"^[a-zA-Z0-9._]+\@[a-zA-Z0-9._]+\.[a-zA-Z]{2,}$", email)!=None:
        return False
    return True

def make_pw_hash_with_salt(name, pw, salt):
    h = hashlib.sha256(name + pw + salt).hexdigest()
    h_string = '%s,%s' % (h, salt)
    return h_string

def get_pages_from_db():
	pages_db = db.GqlQuery("SELECT * FROM PagesDB")
	pages = {}
	for page_db in pages_db:
		page = create_page(page_db.url, page_db.subject, page_db.content,
			page_db.modified, page_db.version)
		pages[page["url"]] = page
	return pages

def get_users_from_db():
	users_db = db.GqlQuery("SELECT * FROM UserDB")
	users = {}
	for user_db in users_db:
		user = create_user(user_db.username, user_db.email, user_db.password_hash)
		users[user["username"]] = user
	if users == {}:
		users = None
	return users


def store_to_memcache(key, value):
	""" Stores a dict of pages to memcache """
	serialized_value = pickle.dumps(value)
	memcache.set(key, serialized_value)
# The intention was to use CAS to avoid race conditions. However,
# the code below does not work - it doesn't store anything in memcacbhe
# so for the time being, memcache.set is used instead
#	client = memcache.Client()
#	i = 0
#	while i < 10:
#		old_pages = client.gets(key)
#		if client.cas(key, serialized_value):
#			break
#		i += 1
#		# In order to avoid a race between two processes waiting the
#		# same amount of time, randomize the wait to be between
#		# 1 and 50 milliseconds
#		waiting_time = random.randint(1,50)
#		time.sleep(waiting_time/1000)

def get_from_memcache(key):
	""" retrieves a value from memcache, and de-serializes it """
	client = memcache.Client()
	value = client.gets(key)
	if value:
		value = pickle.loads(value)
	return value

def create_page(url, subject, content, modified, version):
	""" Creates a new page in the form a dict. """
	p = {}
	p["url"] = url
	p["subject"] = subject
	p["content"] = content
	p["modified"] = modified
	p["version"] = version
	return p

def create_user(username, email, password_hash):
	""" Creates a new user in the form a dict. """
	t = datetime.datetime.now()
	u = {}
	u["username"] = username
	u["email"] = email
	u["password_hash"] = password_hash
	return u

def delete_page(url):
	pages = PagesDB.all()
	for page in pages:
		if page.url == url:
			page.delete()

def insert_page(p):
	t = datetime.datetime.now()
	p["modified"] = t
	# First, remove the old entry from the database
	# delete_page(p["url"])
	# Secondly, store the new page in the database
	print "p=", p
	print p["subject"]
	page = PagesDB(url = p["url"], subject = p["subject"],
		content = p["content"], modified=p["modified"],
		version=p["version"])
	page.put()
	# Then first retrieve the dictionary containing all pages
	# from memcache, update it with the newly inserted page
	# and finally write it back to memcache
	pages = get_from_memcache("pages")
	if not pages:
		pages = {}
	pages[p["url"]] = p
	store_to_memcache("pages", pages)

def insert_user(u):
	user = UserDB(username=u["username"], email=u["email"],
		password_hash=u["password_hash"])
	user.put()
	users = get_from_memcache("users")
	if not users:
		users = {}
	users[u["username"]] = u
	store_to_memcache("users", users)

def get_page(url):
	""" Returns the page for a given url, from memcache or DB """
	pages = get_from_memcache("pages")
	if pages and url in pages:
		return pages[url]
	else:
		pages = get_pages_from_db()
		store_to_memcache("pages", pages)
		if pages and url in pages:
			return pages[url]
		else:
			return None


def get_users():
    users = get_from_memcache("users")
    if not users:
        users = get_users_from_db()
        store_to_memcache("users", users)
    return users

def get_logged_in_user(cookie):
	""" Returns the current user """
	if check_secure_val(cookie):
		return cookie.split('|')[0]
	else:
		return None

def initialize_db_if_necessary():
	""" Checks if DB is empty; if so, creates first page and user """
	users = get_users()
	failed = False
	if not users:
		failed = True
		username = "admin"
		password = "sluring42"
		pw_hash = make_pw_hash(username, password)
		user = create_user("admin", "admin@rudemo.com", pw_hash)
		insert_user(user)
	page = get_page("/")
	if not page:
		failed = True
		page = create_page("/","Welcome to my Wiki!",
			"Content of first wiki page.", "admin", datetime.datetime.now(), 1)
		insert_page(page)
	return failed



############################################
############ HANDLER PAGES #################

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
            self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
            t = jinja_env.get_template(template)
            return t.render(params)

    def render(self, template, **kw):
            self.write(self.render_str(template, **kw))


class MainPage(Handler):
    """ Serve pages at the base URL """
    def get(self):
    	cookie = self.request.cookies.get('username')
    	logged_in_user = get_logged_in_user(cookie)
    	# For the fron page, the URL is not passed as a parameter,
    	# therefore we have to set it ourselves.
    	url = "/"
    	page = get_page(url)
    	if page:
    		self.render("page.html", logged_in_user=logged_in_user,
    			url=page["url"], subject=page["subject"], content=page["content"],
    			modified=page["modified"], version=page["version"])
    	else:
    		new_url = '/_edit'+url
    		self.redirect(new_url)



class TestHandler(Handler):
	def get(self):
		pages = get_from_memcache("pages")
		for p in pages:
			print p


class GetFromMemcache(Handler):
	def get(self):
		pages = get_from_memcache("pages")
		store_to_memcache("pages", pages)


class FillMemcache(Handler):
	def get(self):
		pages = get_pages_from_db()
		store_to_memcache("pages", pages)


class LogoutPage(Handler):
    def get(self):
        nullString = ""
        self.response.headers.add_header('Set-Cookie',
        	'username=%s; Path=/' % nullString)
        time.sleep(0.2)
        self.redirect('/')


class LoginPage(Handler):
    def post(self):
    	if initialize_db_if_necessary():
    		self.redirect("/")
        username = self.request.get("username")
        password = self.request.get("password")
        users = get_users()
        error = None
        if users:
	        for user in users:
	            if users[user]["username"] == username:
	                salt = users[user]["password_hash"].split(',')[1]
	                password_hash = make_pw_hash_with_salt(username, password,
	                	salt)
	                if password_hash == users[user]["password_hash"]:
	                    self.response.headers.add_header('Set-Cookie',
	                    	'username=%s' % make_secure_val(username))
	                    self.redirect("/")
	                else:
	                    error="Incorrect login"
	                    self.render("login.html", error=error,
	                    	message=True)
	                return
        error="Incorrect login"
        self.render("login.html", error=error, message=False)
   
    def get(self):
    	cookie = self.request.cookies.get('username')
    	logged_in_user = get_logged_in_user(cookie)
        self.render("login.html", logged_in_user=logged_in_user)


class SignupPage(Handler):
    def post(self):
        username = self.request.get("username")
        email = self.request.get("email")
        if email == "":
        	# Udacity's grader does'nt provide email address
            email = "default@email.com" 
        password = self.request.get("password")
        verify = self.request.get("verify")
        users = get_users()
        error_message = None
        error_field = None
        if users:
        	for user in users:
        		if username == users[user]["username"]:
        			error_message = "That user already exists."
        			error_field = "username"
        			print error
        			break
        	if email == users[user]["email"]:
        		error_message = "Email address already exists."
        		error_field = "email"
        if error_message:
        	self.render("signup.html", error_message=error_message,
        		username=username, email = email, password=password, verify=verify)
        elif is_username_invalid(username):
        	error_message = "The username is invalid\
        		Only use a-zA-Z0-9. Minimum two characters."
        	error_field = "username"
        	self.render("signup.html", error_message=error_message,
        		error_field = error_field, username=username,
        		email = email, password=password, verify=verify)
        elif password != verify:
        	error_message = "The passwords do not match"
        	error_field = "password"
        	self.render("signup.html", error_message=error_message,
        		error_field = error_field, username=username,
        		email = email)
        elif is_password_invalid(password):
        	error_message = "Passwords contain illegal characters. \
        		Only use a-zA-Z0-9. Minimum four characters."
        	error_field = "password"
        	self.render("signup.html", error_message=error_message,
        		error_field = error_field, username=username,
        		email = email)
        elif is_email_invalid(email):
        	error_message = "The email address is invalid"
        	error_field = "email"
        	self.render("signup.html", error_message=error_message,
        		error_field = error_field, username=username,
        		email = email, password=password, verify=verify)
        else:
        	password_hash = make_pw_hash(username, password)
        	self.response.set_cookie('username',
        		make_secure_val(username), path='/')
        	new_user = create_user(username, email, password_hash)
        	insert_user(new_user)
        	time.sleep(0.2)
        	self.redirect("/")

    def get(self):
    	cookie = self.request.cookies.get('username')
    	logged_in_user = get_logged_in_user(cookie)
        self.render("signup.html", logged_in_user=logged_in_user)


class EditPage(Handler):
	def get(self, url):
		cookie = self.request.cookies.get('username')
		logged_in_user = get_logged_in_user(cookie)
		if logged_in_user:
			if url == "/_edit":
				url = "/"
			page = get_page(url)
			if page:
				subject = page["subject"]
				content = page["content"]
				created = page["created"]
				version = page["version"]
			else:
				subject = url[1:]
				content = ""
				cookie = self.request.cookies.get('username')
				created = datetime.datetime.now()
				version = 0
			self.render("edit_page.html", logged_in_user= logged_in_user,
				url=url, subject=subject, content=content,
				created=created, version=version)
		else:
			self.redirect('/login')

	def post(self, url):
		page = {}
		page["url"] = url
		page["subject"] = url[1:]
		page["content"] = self.request.get("content")
		page["created"] = self.request.get("created")
		page["version"] = self.request.get("version")
		if not page["version"]:
			print "Not page, version=1"
			page["version"] = 1
		else:
			print "Page, version increment"
			page["version"] = int(page["version"])+1
 		print "post p:", page
		insert_page(page)
		time.sleep(0.2)
		self.redirect(url)

class HistoryPage(Handler):
	def get(self, url):
		pass


class WikiPage(Handler):
    def get(self, url):
    	cookie = self.request.cookies.get('username')
    	logged_in_user = get_logged_in_user(cookie)
    	page = get_page(url)
    	if page:
    		self.render("page.html", logged_in_user=logged_in_user,
    			url=page["url"], subject=page["subject"],
    			content=page["content"])
    	else:
    		new_url = '/_edit'+url
    		self.redirect(new_url)


app = webapp2.WSGIApplication([
	(r'/?', MainPage),
	(r'/logout/?', LogoutPage),
	(r'/login/?', LoginPage),
	(r'/signup/?', SignupPage),
	(r'/_test', TestHandler),
	(r'/_edit'+PAGE_RE, EditPage),
	(r'/_history'+PAGE_RE, HistoryPage),
	(r'/_get_from_memcache', GetFromMemcache),
	(r'/_fillmemcache',FillMemcache),
    (PAGE_RE, WikiPage),
        ],
                                                                debug = True)
