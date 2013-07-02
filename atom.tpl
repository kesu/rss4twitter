<?xml version="1.0" encoding="utf-8"?>
{% autoescape true %}
<feed xmlns="http://www.w3.org/2005/Atom">
	<title>{{ user_name }} on Twitter</title>
	<link href="{{ twitter_url }}/{{user_name }}"/>
	<updated>{{ time_now }}</updated>
	<author><name>rss4twitter</name></author>
	<id>{{ twitter_url }}/{{user_name }}</id>
	{% for id,tweet in tweet_list.iteritems() %}
	<entry>
	    <title>{{ user_name }}:{{ tweet[0] }} </title>
	    <link href="{{ twitter_url+tweet[2] }}"/>
	    <id>{{ tweet[2] }}</id>
	    <updated>{{ tweet[1] }}</updated>
	    <summary>{{ tweet[0] }} </summary>
	</entry>
	{% endfor %}
</feed>
{% endautoescape %}