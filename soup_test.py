from BeautifulSoup import Tag
from BeautifulSoup import BeautifulSoup
from BeautifulSoup import SoupStrainer
import urllib2

from jinja2 import Template
from jinja2 import Environment, PackageLoader
from datetime import datetime


atom_template = 'atom.tpl'


def getTweetsForUser(user_name, max_id):
    t_url = "http://twitter.com/" + user_name
    headers = { 'User-Agent' : 'Mozilla/5 (Solaris 10) Gecko', 'Accept-Language':'en-US,en;q=0.8'}
    request = urllib2.Request(t_url, None, headers)
    response = urllib2.urlopen(request)
    #soup = BeautifulSoup(response)
    soup = BeautifulSoup(response, convertEntities=BeautifulSoup.HTML_ENTITIES)
    stream_container = soup.find ('div', 'stream-container')
    data_since_id = stream_container['data-since-id']
    print data_since_id

    tweet_list = {}
    if max_id >= data_since_id:
        return tweet_list

    stream_items = stream_container.findAll('li','stream-item')
    for stream_item in stream_items:
        tweet_item_id = stream_item['data-item-id']
        tweet_item_timestamp = stream_item.find('a','tweet-timestamp')['title']   #time.strptime("4:00 AM - 30 Jun 13", "%I:%M %p - %d %b %y")
        tweet_item_link = stream_item.find('a','tweet-timestamp')['href']
        #print tweet_item_time
        tweet_text_contents = stream_item.find(None,'tweet-text').contents
        tweet_item_text = ''.join(item.text if isinstance(item, Tag) else item for item in tweet_text_contents)
        tweet_list[tweet_item_id] = [tweet_item_text, tweet_item_timestamp, tweet_item_link]

    for k,v in tweet_list.iteritems():
        print k,v[0],v[1],v[2]

    print max(tweet_list.keys())
    return data_since_id, tweet_list   

def guess_autoescape(template_name):
    if template_name is None or '.' not in template_name:
        return False
    ext = template_name.rsplit('.', 1)[1]
    return ext in ('html', 'htm', 'xml')

user_name='wired'
t_url = "http://twitter.com/" + user_name
last_id, tweet_list = getTweetsForUser(user_name,1)


env = Environment(autoescape=guess_autoescape, loader=PackageLoader(__name__, '.'), extensions=['jinja2.ext.autoescape'])
template = env.get_template(atom_template)
print template.render(user_name=user_name,twitter_url="http://twitter.com", time_now=datetime.now(), tweet_list=tweet_list)








