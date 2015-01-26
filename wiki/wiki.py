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
import jinja2
import os
import pickle
import random
import time
import unicodedata
import webapp2
from google.appengine.ext import db
from google.appengine.api import memcache

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                                                           autoescape = True)

PAGE_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)'

############################################
############ DATABASE DEFINITIONS ##########

class PagesDB(db.Model):
	""" Class for Pages in the database. """
	url = db.StringProperty(required = True)
	subject = db.StringProperty(required = True)
	content = db.TextProperty(required = True)
	created_by = db.StringProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)
	last_edited = db.DateTimeProperty(required = True, auto_now_add = True)



class UserDB(db.Model):
	""" Class for users in the database. """
	username = db.StringProperty(required = True)
	email = db.StringProperty(required = True)
	password_hash = db.StringProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)


############################################
############ REGULAR CLASS DEFS ############

class Page:
	""" Class for pages when in memory. """
	pass

############################################
############ UTILITY FUNCTIONS #############

def get_pages_from_db():
	pages_db = db.GqlQuery("SELECT * FROM PagesDB ORDER BY created DESC ")
	pages = {}
	for page_db in pages_db:
		page = create_page(page_db.url, page_db.subject, page_db.content,
			page_db.created_by)
		pages[page["url"]] = page
	return pages

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

def create_page(url, subject, content, created_by):
	""" Creates a new page in the form a dict. """
	t = datetime.datetime.now()
	p = {}
	p["url"] = url
	p["subject"] = subject
	p["content"] = content
	p["created_by"] = created_by
	p["created"] = t
	p["last_edited"] = t
	return p

def insert_page(p):
	t = datetime.datetime.now()
	p["last_edited"] = t
	# First store the new page in the database
	page = PagesDB(url = p["url"], subject = p["subject"], content = p["content"],
		created_by = p["created_by"], created = p["created"], last_edited = t)
	page.put()
	# Then first retrieve the dictionary containing all pages
	# from memcache, update it with the newly inserted page
	# and finally write it back to memcache
	pages = get_from_memcache("pages")
	if not pages:
		pages = {}
	pages[p["url"]] = p
	store_to_memcache("pages", pages)

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


def get_user():
	""" Returns the current user """
	# TODO: make this work for real
	return "niklas"


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
        self.render("front.html")

class EditPage(Handler):
	def get(self, url):
		page = get_page(url)
		if page:
			subject = page["subject"]
			content = page["content"]
			created_by = page["created_by"]
			created = page["created"]
		else:
			subject = url[1:]
			content = ""
			created_by = get_user()
			created = datetime.datetime.now()
		self.render("edit_page.html", url=url, subject=subject,
			content=content, created_by=created_by, created=created)

	def post(self, url):
		page = {}
		page["url"] = url
		page["subject"] = self.request.get("subject")
		page["content"] = self.request.get("content")
		page["created_by"] = self.request.get("created_by")
		page["created"] = datetime.datetime.strptime(
			self.request.get("created"), "%Y-%m-%d %H:%M:%S.%f")
		page["last_edited"] = datetime.datetime.now()
		insert_page(page)
		time.sleep(0.2)
		self.redirect(url)


class WikiPage(Handler):
    def get(self, url):
    	page = get_page(url)
    	if page:
    		self.render("page.html", url=page["url"], subject=page["subject"],
    			content=page["content"])
    	else:
    		new_url = '/_edit'+url
    		self.redirect(new_url)


class DebugHandler(Handler):
	def get(self):
		client = memcache.Client()
		p = client.gets("pages")
		print "DEBUG"
		print type(p)
		print p


class TestHandler(Handler):
	def get(self):
		p = create_page("/sundsvall", "sundsvall", "Former tram town in Sweden", "Niklas" )
		page = { "/sundsvall", p}
		memcache.set("pages", pickle.dumps(page))


class GetFromMemcache(Handler):
	def get(self):
		pages = get_from_memcache("pages")
		store_to_memcache("pages", pages)


class FillMemcache(Handler):
	def get(self):
		pages = get_pages_from_db()
		store_to_memcache("pages", pages)


app = webapp2.WSGIApplication([
	(r'/?', MainPage),
	(r'/_debug', DebugHandler),
	(r'/_test', TestHandler),
	(r'/_edit'+PAGE_RE, EditPage),
	(r'/_get_from_memcache', GetFromMemcache),
	(r'/_fillmemcache',FillMemcache),
    (PAGE_RE, WikiPage),
        ],
                                                                debug = True)
