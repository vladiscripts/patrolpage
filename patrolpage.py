#!/usr/bin/env python3
# coding: utf-8
import requests
from urllib.parse import quote
from lxml import etree
import re
# import mwparserfromhell
import pywikibot
import vladi_commons


# не патрулировано
# t = '''<?xml version="1.0"?><api batchcomplete=""><query><normalized><n from="Янковский,_Филипп_Олегович" to="Янковский, Филипп Олегович" /></normalized>
# 	<pages><page _idx="320695" pageid="320695" ns="0" title="Янковский, Филипп Олегович">
# 	<flagged stable_revid="73122852" level="0" level_text="stable" pending_since="2015-09-03T19:47:39Z" /></page></pages></query></api>'''
# # не патрулировалась
# t = '''<?xml version="1.0"?><api batchcomplete=""><query><pages><page _idx="6641104" pageid="6641104" ns="0" title="Таинственная страсть" />				</pages></query></api>'''
# # патрулировано
# t = '''<?xml version="1.0"?><api batchcomplete=""><query><pages><page _idx="13317" pageid="13317" ns="0" title="Саратов">
#         <flagged stable_revid="81687689" level="0" level_text="stable" />     </page></pages></query></api>'''


def page_patrolled(title):
	q_wikiApi_base = 'https://ru.wikipedia.org/w/api.php'
	title = normalization_pagename(str(title))

	# GETparameters = {'action': 'query', 'prop': 'flagged', 'format': 'xml', 'titles': quote(title)}
	# r = requests.get(q_wikiApi_base, data=GETparameters, headers=headers)
	url = q_wikiApi_base + '?action=query&format=xml&prop=flagged&user&utf8=1&redirects=1&titles=' + quote(title)
	headers = {'user-agent': 'user:textworkerBot'}
	r = requests.get(url)

	u = etree.fromstring(r.text)
	if len(u.xpath("//flagged")) == 0 or len(u.xpath("//flagged/@pending_since")) > 0:
		print('не патрулировано: ' + title)
		return False
	else:
		print('патрулировано: ' + title)
		
		return True


def check_links(string):
	global text
	title = re.match(r'\[\[([^|]]+)(\|[^]]+)?\]\]', link).group(1)
	if page_patrolled(title):
		text = text.replace(link, '<s>' + link + '</s>')


def normalization_pagename(t):
	""" Первая буква в верхний регистр, ' ' → '_' """
	t = t.strip()
	return t[0:1].upper() + t[1:].replace(' ', '_')


# wikipages_filename = r'..\temp\AWBfile.txt'
# text = vladi_commons.file_readtext(wikipages_filename)
exclude_namespaces = r'(Special|Служебная|Участник|User|У|Обсуждение[ _]участника|ОУ|Википедия|ВП|Обсуждение[ _]Википедии|Обсуждение):'
close_tpls = re.compile(r'\{\{([Оо]тпатрулировано|[Сс]делано|[Dd]one|[Оо]тклонено)\s*(?:\|.*?)?\}\}')
sections_re = re.compile(r'\n={2,}[^=]+={2,}\n.*?(?=\n={2,}[^=]+={2,}\n|$)', re.DOTALL)
link_re = re.compile(r'\s*(?<!<s>)\s*(\[\[(?!%s).*?\]\])' % exclude_namespaces)
link_title_re = re.compile(r'\[\[([^]|]+).*?\]\]')
link_just_re = re.compile(r'\s*(\[\[(?!%s).*?\]\])' % exclude_namespaces)
tag_li_re = re.compile(r'^[*#](.*)$', re.MULTILINE)
header_re = re.compile(r'^==+([^=]+)==+$', re.MULTILINE)
textend = re.compile(r'\n*$')

site = pywikibot.Site('ru', 'wikipedia')
workpages = ['Википедия:Запросы к патрулирующим', 'Википедия:Запросы к патрулирующим от автоподтверждённых участников']
for workpage in workpages:
	page = pywikibot.Page(site, workpage)
	text = page.get()

	for section in sections_re.findall(text):
		if not close_tpls.search(section) and link_just_re.search(section):
			section_workcopy = section

			links_sections = link_re.findall(section_workcopy)
			links_sections = [x for x in links_sections if x]  # чистка от пустых строк
			for link in links_sections:
				link = [x for x in link if x]  # чистка от пустых строк

				title = link_title_re.match(link[0]).group(1)
				if page_patrolled(title):
					section_workcopy = section_workcopy.replace(link[0], '<s>' + link[0] + '</s>')

				# # тэги li
				# for string in tag_li_re.findall(link[0]):
				# 	check_links(link[0])
				#
				# # заголовки
				# for string in header_re.findall(link[0]):
				# 	check_links(link[0])

			# закрытие разделов
			links_sections = link_re.findall(section_workcopy)
			links_sections = [x for x in links_sections if x]  # чистка от пустых строк
			if not len(links_sections):
				section_workcopy = textend.sub('\n: {{отпатрулировано}}. --~~~~\n',
											   section_workcopy)  # [[У:textworkerBot | textworkerBot]]

			text = text.replace(section, section_workcopy)

	# Запись страниц
	# vladi_commons.file_savetext(wikipages_filename, text)
	page.text = text
	edit_comment = 'зачеркнуто отпатрулированное'
	# page.save(edit_comment)
