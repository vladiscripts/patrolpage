#!/usr/bin/env python3
# coding: utf8
#
# author: https://github.com/vladiscripts
#
# API's doc: https://ru.wikipedia.org/w/api.php?action=help&modules=query%2Bflagged
import requests
import re
import pywikibot


def pageInfoFromAPI(title):
	params = {'action': 'query', 'prop': 'flagged|info', 'titles': title,
			  'format': 'json', 'utf8': 1, }  # 'redirects': 1
	r = requests.get(url='https://ru.wikipedia.org/w/api.php', params=params)
	for pageInfo in r.json()['query']['pages'].values():
		return pageInfo


def pagePatrolled(p):
	if not 'flagged' in p or 'pending_since' in p['flagged']:
		# print('не патрулировано: ' + title)
		return False
	else:
		# print('патрулировано: ' + title)
		return True


namespacesExcluded = r'(Special|Служебная|Участник|User|У|Обсуждение[ _]участника|ОУ|Википедия|ВП|Обсуждение[ _]Википедии|Обсуждение):'
close_tpls = re.compile(r'\{\{([Оо]тпатрулировано|[Сс]делано|[Dd]one|[Оо]тклонено)\s*(?:\|.*?)?\}\}')
sections_re = re.compile(r'\n={2,}[^=]+={2,}\n.*?(?=\n={2,}[^=]+={2,}\n|$)', re.DOTALL)
linkNotStriked_re = re.compile(r'\s*(?<!<s>)\s*(\[\[(?!%s).*?\]\])' % namespacesExcluded)
linkTitle_re = re.compile(r'\[\[([^]|]+).*?\]\]')
linkJust_re = re.compile(r'\s*(\[\[(?!%s).*?\]\])' % namespacesExcluded)
textEnd = re.compile(r'\n*$')

site = pywikibot.Site('ru', 'wikipedia')
workpages = ['Википедия:Запросы к патрулирующим', 'Википедия:Запросы к патрулирующим от автоподтверждённых участников']
for workpage in workpages:
	is_patrolled = False
	is_autoclosing = False
	page = pywikibot.Page(site, workpage)
	textPage = page.get()

	for section in sections_re.findall(textPage):
		if not close_tpls.search(section) and linkJust_re.search(section):
			section_original = section
			redirectsFound = set()

			links_sections = linkNotStriked_re.findall(section)
			for link in links_sections:
				title = linkTitle_re.match(link[0]).group(1)
				pageProperties = pageInfoFromAPI(title)
				is_patrolled = pagePatrolled(pageProperties)
				if is_patrolled:
					section = section.replace(link[0], '<s>%s</s>' % link[0])
				if 'redirect' in pageProperties:
					redirectsFound.add(title)

			# закрытие разделов со сделаными запросами
			links_sections = linkNotStriked_re.findall(section)
			if not len(links_sections):
				if len(redirectsFound) == 0:
					section = textEnd.sub('\n: {{отпатрулировано}} участниками. --~~~~\n', section)
				else:
					section = textEnd.sub(
						'\n: {{отпатрулировано}} участниками. В запросе были перенаправления: %s. --~~~~\n' % \
						', '.join(['[[%s]]' % t for t in redirectsFound]),
						section)
				is_autoclosing = True

			textPage = textPage.replace(section_original, section)

	# Пост страницы
	if is_patrolled or is_autoclosing:
		page.text = textPage
		summary = 'зачеркнуто отпатрулированное, автоитог' if is_autoclosing else 'зачеркнуто отпатрулированное'
		page.save(summary)
