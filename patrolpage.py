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


if __name__ == '__main__':
	namespacesExcluded = r'(Special|Служебная|Участник|User|У|Обсуждение[ _]участника|ОУ|Википедия|ВП|Обсуждение[ _]Википедии|Обсуждение):'
	closing_tpls = re.compile(r'\{\{([Оо]тпатрулировано|[Сс]делано|[Dd]one|[Оо]тклонено)\s*(?:\|.*?)?\}\}')
	sections_re = re.compile(r'\n={2,}[^=]+={2,}\n.*?(?=\n={2,}[^=]+={2,}\n|$)', re.DOTALL)
	linkNotStriked_re = re.compile(r'\s*(?<!<s>)\s*(\[\[(?!%s).*?\]\])' % namespacesExcluded)
	linkTitle_re = re.compile(r'\[\[([^]|]+).*?\]\]')
	link_re = re.compile(r'\s*(\[\[(?!%s).*?\]\])' % namespacesExcluded)
	textEnd = re.compile(r'\n*$')

	# Параметр "user" нужен при наличии разноименных ботов на одном аккаунте tool.wmflab.org
	# В другом случае лучше его удалить
	site = pywikibot.Site('ru', 'wikipedia', user='TextworkerBot')

	workpages = ['Википедия:Запросы к патрулирующим',
				 'Википедия:Запросы к патрулирующим от автоподтверждённых участников']
	for workpage in workpages:
		found_page_patrolled = False
		was_closed_section = False
		page = pywikibot.Page(site, workpage)
		textPage = page.get()

		# Проверка разделов
		for section in sections_re.findall(textPage):
			if link_re.search(section) and not closing_tpls.search(section):
				section_original = section
				redirectsFound = set()

				# Проверка ссылок в разделе
				links_sections = linkNotStriked_re.findall(section)
				for link in links_sections:
					title = linkTitle_re.match(link[0]).group(1)
					pageProperties = pageInfoFromAPI(title)
					is_patrolled = pagePatrolled(pageProperties)
					if is_patrolled:
						# ссылка отптрулирована
						section = section.replace(link[0], '<s>%s</s>' % link[0])
						found_page_patrolled = True
					if 'redirect' in pageProperties:
						# ссылка является перенаправлением
						redirectsFound.add(title)

				# Закрытие разделов с отработанными запросами
				links_sections = linkNotStriked_re.findall(section)
				if not len(links_sections):
					if len(redirectsFound) == 0:
						section = textEnd.sub('\n: {{отпатрулировано}} участниками. --~~~~\n', section)
					else:
						section = textEnd.sub(
							'\n: {{отпатрулировано}} участниками. В запросе были перенаправления: %s. --~~~~\n' % \
							', '.join(['[[%s]]' % t for t in redirectsFound]),
							section)
					was_closed_section = True

				textPage = textPage.replace(section_original, section)

		# Постинг
		if found_page_patrolled or was_closed_section:
			page.text = textPage
			summary = 'зачеркнуто отпатрулированное, автоитог' if was_closed_section else 'зачеркнуто отпатрулированное'
			page.save(summary)
