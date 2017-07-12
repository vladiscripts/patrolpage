#!/usr/bin/env python3
# coding: utf8
#
# author: https://github.com/vladiscripts
#
# API's doc: https://ru.wikipedia.org/w/api.php?action=help&modules=query%2Bflagged
import requests
from lxml import etree
import re
import pywikibot


def page_patrolled(title):
	params = {'action': 'query', 'prop': 'flagged', 'format': 'xml', 'titles': title, }  # 'redirects': 1
	r = requests.get(url='https://ru.wikipedia.org/w/api.php', params=params)
	flags = etree.fromstring(r.text)
	if len(flags.xpath("//flagged")) == 0 or len(flags.xpath("//flagged/@pending_since")) > 0:
		print('не патрулировано: ' + title)
		return False
	else:
		print('патрулировано: ' + title)
		return True


exclude_namespaces = r'(Special|Служебная|Участник|User|У|Обсуждение[ _]участника|ОУ|Википедия|ВП|Обсуждение[ _]Википедии|Обсуждение):'
close_tpls = re.compile(r'\{\{([Оо]тпатрулировано|[Сс]делано|[Dd]one|[Оо]тклонено)\s*(?:\|.*?)?\}\}')
sections_re = re.compile(r'\n={2,}[^=]+={2,}\n.*?(?=\n={2,}[^=]+={2,}\n|$)', re.DOTALL)
link_re = re.compile(r'\s*(?<!<s>)\s*(\[\[(?!%s).*?\]\])' % exclude_namespaces)
linkTitle_re = re.compile(r'\[\[([^]|]+).*?\]\]')
link_just_re = re.compile(r'\s*(\[\[(?!%s).*?\]\])' % exclude_namespaces)
textend = re.compile(r'\n*$')

site = pywikibot.Site('ru', 'wikipedia')
workpages = ['Википедия:Запросы к патрулирующим', 'Википедия:Запросы к патрулирующим от автоподтверждённых участников']
for workpage in workpages:
	is_patrolled = False
	is_autoclosing = False
	page = pywikibot.Page(site, workpage)
	textPage = page.get()

	for section in sections_re.findall(textPage):
		if not close_tpls.search(section) and link_just_re.search(section):
			section_original = section

			links_sections = link_re.findall(section)
			for link in links_sections:

				title = linkTitle_re.match(link[0]).group(1)
				if page_patrolled(title):
					section = section.replace(link[0], '<s>%s</s>' % link[0])
					is_patrolled = True

			# закрытие разделов со сделаными запросами
			links_sections = link_re.findall(section)
			if not len(links_sections):
				is_autoclosing = True
				section = textend.sub('\n: {{отпатрулировано}} участниками. --~~~~\n', section)

			textPage = textPage.replace(section_original, section)

	# Пост страницы
	if is_patrolled or is_autoclosing:
		page.text = textPage
		summary = 'зачеркнуто отпатрулированное, автоитог' if is_autoclosing else 'зачеркнуто отпатрулированное'
		page.save(summary)
