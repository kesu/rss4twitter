<?xml version="1.0" encoding="utf-8"?>
{% autoescape true %}
<feed xmlns="http://www.w3.org/2005/Atom">
	<title>{{ user_name }} on Twitter</title>
	<link href="{{ twitter_url }}/{{user_name }}"></link>
	<updated>{{ time_now }}</updated>
	<author><name>rss4twitter</name></author>
	<id>{{ twitter_url }}/{{user_name }}</id>
	{% for tweet in tweet_list %}
	<entry>
	    <title>{{ user_name }}:{{ tweet[1] }} </title>
	    <link href="{{ twitter_url+tweet[3] }}"></link>
	    <id>{{ tweet[3] }}</id>
	    <updated>{{ tweet[2] }}</updated>
	    <summary>{{ tweet[1] }} </summary>
	</entry>
	{% endfor %}
</feed>
{% endautoescape %}