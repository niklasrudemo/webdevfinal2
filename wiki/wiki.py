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

import os
import logging
import time
import unicodedata
import jinja2
import webapp2

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                                                           autoescape = True)

PAGE_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)'
DATABASE = {}

def insert_page(url, subject, content):
	global DATABASE
	DATABASE[url] = (subject, content)

def get_page(url):
	global DATABASE
	if url in DATABASE:
		return DATABASE[url][0], DATABASE[url][1]
	else:
		return None

def debug():
	global DATABASE
	print "DATABASE: ", DATABASE

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
			subject, content = page
		else:
			subject = url[1:]
			content = ""
		debug()
		self.render("edit_page.html", url = url, subject=subject, content=content)

	def post(self, url):
		subject = self.request.get("subject")
		content = self.request.get("content")
		insert_page(url, subject, content)
		debug()
		print "url: ", url
		self.redirect(url)


class WikiPage(Handler):
    def get(self, url):
    	print "WikiPage!"
    	print "URL=%s" %url
    	page = get_page(url)
    	if page:
    		subject = page[0]
    		content = page[1]
    		debug()
    		self.render("page.html", url=url, subject=subject, content=content)
    	else:
    		new_url = '/_edit'+url
    		print "New-URL: %s" % new_url
    		debug()
    		self.redirect(new_url)


class DebugHandler(Handler):
	def get(self):
		if DATABASE == {}:
			print "Database empty"
		else:
			print "Database: ", DATABASE


app = webapp2.WSGIApplication([
	(r'/?', MainPage),
	(r'/_debug', DebugHandler),
	(r'/_edit'+PAGE_RE, EditPage),
    (PAGE_RE, WikiPage),
        ],
                                                                debug = True)
