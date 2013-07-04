import webapp2
import os
import logging
import urllib2
from operator import itemgetter
from urllib2 import HTTPError, URLError

from datetime import datetime, timedelta
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.runtime import apiproxy_errors

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
        self.timeout = 3600
        self.cache_timeout = 3600

    def tweetsToRSS(self, user_name,tweet_list):
        return template.render(user_name=user_name,
            twitter_url="http://twitter.com",
            time_now=datetime.now().isoformat("T"),
            tweet_list=tweet_list)

    def getTweetsForUser(self, user_name, max_id):
        tweet_list = []
        t_url = self.twitter_url + user_name
        headers = { 'User-Agent' : 'Mozilla/5 (Solaris 10) Gecko', 'Accept-Language':'en-US,en;q=0.8'}
        request = urllib2.Request(t_url, None, headers)
        try:
            response = urllib2.urlopen(request)
        except HTTPError as e:
            logging.error("HTTP Error while fetching " + user_name + " Error code:" + str(e.code))
            raise
        except URLError as e:
            logging.error("Failed to connect to twitter Reason: " + e.reason)
            raise
        soup = BeautifulSoup(response, convertEntities=BeautifulSoup.HTML_ENTITIES)
        stream_container = soup.find ('div', 'stream-container')
        data_since_id = stream_container['data-since-id']

        if max_id >= data_since_id:
            return None, None

        stream_items = stream_container.findAll('li','stream-item')
        for stream_item in stream_items:
            tweet_item_id = stream_item['data-item-id']
            tweet_item_timestamp = stream_item.find('a','tweet-timestamp')['title']
            tweet_item_timestamp = datetime.strptime(tweet_item_timestamp, "%I:%M %p - %d %b %y").isoformat("T") # convert time to RFC 3339 format
            tweet_item_link = stream_item.find('a','tweet-timestamp')['href']
            tweet_text_contents = stream_item.find(None,'tweet-text').contents
            tweet_item_text = ''.join(item.text if isinstance(item, Tag) else item for item in tweet_text_contents)
            tweet_list.append([tweet_item_id, tweet_item_text, tweet_item_timestamp, tweet_item_link])

        tweet_list.sort(key=itemgetter(2))
        return data_since_id, tweet_list

    def fetchRSSFromDB(self, user_name):
        cache_result = memcache.get(user_name)
        if cache_result:
            time_delta = (datetime.now() - cache_result.u_tweet_since_time).total_seconds()
            if (time_delta < self.timeout):
                #loggin.debug("Fetched from cache for user:" + user_name + ", time delta is: " + str(time_delta))
                return cache_result.u_tweet_since_id, cache_result.u_rss, cache_result.u_tweet_since_time
            #else:
                #loggin.debug("Fetched from cache, but time delta expired for:" + user_name + ", time delta is: " + str(time_delta))
        #else:
            #loggin.debug("Cache miss for user:" + user_name)
        return None, None, None # Data Store Disable ###########
        q = db.GqlQuery("SELECT * FROM UserRss WHERE u_user = :1 LIMIT 1", user_name)
        results = q.get()
        if results:
            time_delta = (datetime.now() - results.u_tweet_since_time).total_seconds()
            if (time_delta > self.timeout):
                #loggin.debug("Timout expired - Entry is " + str(time_delta) + " seconds old. Deleting entry from DB")
                db.delete(results)
                return None, None, None
            memcache.set(user_name, results, self.cache_timeout)
            return results.u_tweet_since_id, results.u_rss, results.u_tweet_since_time
        else:
            return None, None, None

    def saveRSSToDB(self, user_name, rss_text, last_tweet_id, tweet_since_time):
        u = UserRss(u_user=user_name, u_rss=rss_text, u_tweet_since_id=long(last_tweet_id),u_tweet_since_time=tweet_since_time)
        memcache.set(user_name, u, self.cache_timeout)
        #u.put()  # Data Store Disable ###########

    def get(self):        
        ua = self.request.headers['User-Agent']
        if "Yahoo Pipes" in ua:
            logging.info("Blocked Yahoo Pipes")
            return self.response.set_status(401)

        HTTP_HEADER_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"
        user_name = self.request.get('name').lstrip('@')

        h_if_modified_since = self.request.headers.get('If-Modified-Since','None')
        h_if_none_match = self.request.headers.get('If-None-Match','None')
        tweet_since_id, user_rss, tweet_since_time = self.fetchRSSFromDB(user_name)

        if user_rss:
            # log_compare ="tweet_since_id=" + str(tweet_since_id) + "; h_if_none_match=" + "; h_if_modified_since=" + h_if_modified_since
            # log_compare += "; tweet_since_time=" + tweet_since_time.strftime(HTTP_HEADER_FORMAT)
            # logging.info (log_compare);

            if (h_if_none_match == '"'+ str(tweet_since_id) + '"' and h_if_modified_since == tweet_since_time.strftime(HTTP_HEADER_FORMAT)):
                logging.debug("Not changed - 304")
                return self.response.set_status(304)
        if (user_rss is None):
            #loggin.debug("Fetching tweets for " + user_name + " from twitter.com.")
            try:
                tweet_since_id, tweet_list = self.getTweetsForUser(user_name, tweet_since_id)
                if tweet_list:
                    user_rss = self.tweetsToRSS(user_name, tweet_list)
                    #loggin.debug("Save RSS to DB for " + user_name)
                    tweet_since_time = datetime.utcnow()
                    self.saveRSSToDB(user_name, user_rss, tweet_since_id, tweet_since_time)
            except (HTTPError, URLError):
                return self.redirect("/404.html")

        self.response.headers["Last-Modified"] = tweet_since_time.strftime(HTTP_HEADER_FORMAT)
        self.response.headers["ETag"] = '"' + str(tweet_since_id) + '"'
        sixty_minutes_in_seconds = 60*60
        expires_time = datetime.utcnow() + timedelta(seconds=sixty_minutes_in_seconds)
        self.response.headers["Expires"] = expires_time.strftime(HTTP_HEADER_FORMAT)
        self.response.headers["Cache-Control"] = "public, max-age=%s" % sixty_minutes_in_seconds

        self.response.write(user_rss)

application = webapp2.WSGIApplication([
    ('/getrss', GetRssForUser),
], debug=False)

atom_template_file = 'atom.tpl'
env = Environment(autoescape=True,
    loader=FileSystemLoader('.'),
    auto_reload=True,
    cache_size=0,
    extensions=['jinja2.ext.autoescape'])
template = env.get_template(atom_template_file)
#loggin.debug("Templated loaded")
