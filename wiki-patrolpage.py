# coding: utf-8
import re
import vladi_commons
import mwparserfromhell
import requests, wikiapi
from urllib.parse import quote


# wikipages_filename = r'..\temp\patrolpage.txt'
wikipages_filename = r'..\temp\AWBfile.txt'
text = vladi_commons.file_readtext(wikipages_filename)
# wikicode = mwparserfromhell.parse(text)

def page_patrolled(title):
	q_wikiApi_base = 'https://ru.wikipedia.org/w/api.php'
	title = wikiapi.normalization_pagename(str(title))
	# title = wikiapi.normalization_pagename('Янковский, Филипп Олегович')
	# url = q_wikiApi_base + title

	GETparameters = {'action': 'query', 'prop': 'flagged', 'format': 'xml', 'titles': quote(title)}
	url = q_wikiApi_base + '?action=query&format=xml&prop=flagged&redirects=1&titles=' + quote(title)
	headers = {'user-agent': 'user:textworkerBot'}
	r = requests.get(url)
	# r = requests.get(q_wikiApi_base, data=GETparameters, headers=headers)
	# flafpatrol = r.json()
	from lxml import etree
	# не патрулировано
	# t = '''<?xml version="1.0"?><api batchcomplete=""><query><normalized><n from="Янковский,_Филипп_Олегович" to="Янковский, Филипп Олегович" /></normalized>
	# 	<pages><page _idx="320695" pageid="320695" ns="0" title="Янковский, Филипп Олегович">
	# 	<flagged stable_revid="73122852" level="0" level_text="stable" pending_since="2015-09-03T19:47:39Z" /></page></pages></query></api>'''
	# # не патрулировалась
	# t = '''<?xml version="1.0"?><api batchcomplete=""><query><pages><page _idx="6641104" pageid="6641104" ns="0" title="Таинственная страсть" />				</pages></query></api>'''
	# # патрулировано
	# t = '''<?xml version="1.0"?><api batchcomplete=""><query><pages><page _idx="13317" pageid="13317" ns="0" title="Саратов">
	#         <flagged stable_revid="81687689" level="0" level_text="stable" />     </page></pages></query></api>'''
	# u = etree.fromstring(t)
	u = etree.fromstring(r.text)
	if len(u.xpath("//flagged")) == 0 or len(u.xpath("//flagged/@pending_since")) > 0:
		# if len(u.xpath("//flagged")) == 0 or (len(u.xpath("//flagged")) > 0 and len(u.xpath("//flagged/@pending_since")) > 0):
		print('не патрулировано: ' + title)
		return False
	else:
		print('патрулировано: ' + title)
	return True


def check_links(string):
	global text
	for link in re.findall(r'\s*(?<!<s>)\s*(\[\[.*?\]\])', string):
		if re.match(exclude_namespaces, link) is None:
			title = re.match(r'\[\[(.*)\|?.*\]\]', link).group(1)
			if page_patrolled(title):
				text = text.replace(link, '<s>' + link + '</s>')



exclude_namespaces = r'\[\[(?:Special|Служебная|Участник|User|У|Обсуждение[ _]участника|ОУ|Википедия|ВП|Обсуждение[ _]Википедии|Обсуждение):'


# тэги li
for string in re.findall(r'^[*#](.*)$', text, re.MULTILINE):
	check_links(string)

# заголовки
for string in re.findall(r'^==+([^=]+)==+$', text, re.MULTILINE):
	check_links(string)
	pass

pass

# регистр букв заголовков в строчные ------
# for tag in wikicode.filter_tags():
# 	if tag.wiki_markup == '*' or tag.wiki_markup == '#':
# 		if tag != 'li':
# 			if tag.contents:
# 				content = tag.contents

# text = str(wikicode)
# print(text)
vladi_commons.file_savetext(wikipages_filename, text)
pass