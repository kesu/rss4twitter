import webapp2
import os
import logging
import urllib2

from urllib2 import HTTPError, URLError

from datetime import datetime
from google.appengine.ext import db

from jinja2 import Template, Environment, FileSystemLoader

from BeautifulSoup import BeautifulSoup, Tag

# class Tweet(db.Model):
#   t_user = db.StringProperty(required=True)
#   t_tweet_text = db.TextProperty(required=True)  
#   t_datetime = db.DateTimeProperty()

#   def toDict(self):
#         return { str(self.t_user) : [str(self.t_tweet_text), str(t_datetime)] }

# def guess_autoescape(template_name):
#     if template_name is None or '.' not in template_name:
#         return False
#     ext = template_name.rsplit('.', 1)[1]
#     return ext in ('html', 'htm', 'xml', 'tpl')

class UserRss(db.Model):
    u_user = db.StringProperty(required=True)
    u_rss = db.TextProperty()
    u_tweet_since_time = db.DateTimeProperty()
    u_tweet_since_id = db.IntegerProperty()

class GetRssForUser(webapp2.RequestHandler):

    def __init__(self, request, response):
        self.initialize(request, response)    
        self.twitter_url = "http://twitter.com/"
        self.timeout = 5
        logging.error("__init__")        

    def tweetsToRSS(self, user_name,tweet_list):
        return template.render(user_name=user_name,
            twitter_url="http://twitter.com", 
            time_now=datetime.now(), 
            tweet_list=tweet_list)

    def getTweetsForUser(self, user_name, max_id):
        t_url = self.twitter_url + user_name
        headers = { 'User-Agent' : 'Mozilla/5 (Solaris 10) Gecko', 'Accept-Language':'en-US,en;q=0.8'}
        request = urllib2.Request(t_url, None, headers)
        try:
            response = urllib2.urlopen(request)
        except HTTPError as e:
            logging.error("HTTP Error while fetching " + user_name + " Error code:", e.code)
            raise
        except URLError as e:
            logging.error("Failed to connect to twitter Reason: " + e.reason)
            raise
        soup = BeautifulSoup(response, convertEntities=BeautifulSoup.HTML_ENTITIES)
        stream_container = soup.find ('div', 'stream-container')
        data_since_id = stream_container['data-since-id']

        tweet_list = {}
        if max_id >= data_since_id:
            return -1, tweet_list

        stream_items = stream_container.findAll('li','stream-item')
        for stream_item in stream_items:
            tweet_item_id = stream_item['data-item-id']
            tweet_item_timestamp = stream_item.find('a','tweet-timestamp')['title']     #time.strptime("4:00 AM - 30 Jun 13", "%I:%M %p - %d %b %y")
            tweet_item_link = stream_item.find('a','tweet-timestamp')['href']
            #print tweet_item_time
            tweet_text_contents = stream_item.find(None,'tweet-text').contents
            tweet_item_text = ''.join(item.text if isinstance(item, Tag) else item for item in tweet_text_contents)
            tweet_list[tweet_item_id] = [tweet_item_text, tweet_item_timestamp, tweet_item_link]

        print max(tweet_list.keys())
        return data_since_id, tweet_list

    def fetchRSSFromDB(self, user_name):
        q = db.GqlQuery("SELECT * FROM UserRss where u_user = :1", user_name)
        results = q.get()
        if results:
            time_delta = (datetime.now() - results.u_tweet_since_time).total_seconds()
            return time_delta, results.u_tweet_since_id, results.u_rss
        else:
            return self.timeout+1, None, None

    def saveRSSToDB(self, user_name, rss_text, last_tweet_id):
        q = db.GqlQuery("SELECT __key__ FROM UserRss where u_user = :1", user_name)
        results = q.fetch(10)
        db.delete(results)
        u = UserRss(u_user=user_name, u_rss=rss_text, u_tweet_since_id=long(last_tweet_id),u_tweet_since_time=datetime.now())
        u.put()

    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        user_name = self.request.get('name')

        time_delta_in_seconds, tweet_since_id, user_rss = self.fetchRSSFromDB(user_name)        
        if ( time_delta_in_seconds < self.timeout and user_rss is not None):
            rss_text = user_rss
        else:
            try:
                last_tweet_id, tweet_list = self.getTweetsForUser(user_name, tweet_since_id)
                logging.error("tweet_since_id: " + str(tweet_since_id))
                logging.error("last_tweet_id:  " + str(last_tweet_id))
                logging.error(long(last_tweet_id) == tweet_since_id)
                if last_tweet_id != -1:
                    rss_text = self.tweetsToRSS(user_name, tweet_list)
                    self.saveRSSToDB(user_name, rss_text, last_tweet_id)
                    logging.error(len(tweet_list))
                else:
                    rss_text = user_rss
            except (HTTPError, URLError):
                return self.redirect("https://github.com/404")
        self.response.headers["Content-Type"] = "application/rss+xml"
        self.response.write(rss_text)

application = webapp2.WSGIApplication([
    ('/getrss', GetRssForUser),
], debug=True)

atom_template_file = 'atom.tpl'
env = Environment(autoescape=True, 
    loader=FileSystemLoader('.'),
    auto_reload=True,
    cache_size=0, 
    extensions=['jinja2.ext.autoescape'])
template = env.get_template(atom_template_file)
logging.error("__end__")