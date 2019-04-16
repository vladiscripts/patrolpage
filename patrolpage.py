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
        page_text = page.get()

        # Проверка разделов
        for section in sections_re.findall(page_text):
            if link_re.search(section) and not closing_tpls.search(section):
                section_original = section
                redirects_found = set()

                # Проверка ссылок в разделе, зачёркивание
                wikilinks = linkNotStriked_re.findall(section)
                for link in wikilinks:
                    title = linkTitle_re.match(link).group(1)
                    pageProperties = pageInfoFromAPI(title)
                    is_patrolled = pagePatrolled(pageProperties)
                    if is_patrolled:
                        # ссылка отптрулирована
                        found_page_patrolled = True
                        section = section.replace(link, '<s>%s</s>' % link)  # зачёркиваем
                    if 'redirect' in pageProperties:
                        # ссылка является перенаправлением
                        redirects_found.add(title)

                # Закрытие разделов с отработанными запросами
                wikilinks = linkNotStriked_re.findall(section)
                if not wikilinks:
                    section = section.rstrip()
                    if not redirects_found:
                        section = textEnd.sub('\n: {{отпатрулировано}} участниками. --~~~~\n', section)
                    else:
                        section = textEnd.sub(
                            '\n: {{отпатрулировано}} участниками. В запросе были перенаправления: %s. --~~~~\n' % \
                            ', '.join(['[[%s]]' % t for t in redirects_found]),
                            section)
                    was_closed_section = True

                page_text = page_text.replace(section_original, section)

        # Постинг
        if found_page_patrolled or was_closed_section:
            page.text = page_text
            summary = 'зачеркнуто отпатрулированное, автоитог' if was_closed_section else 'зачеркнуто отпатрулированное'
            page.save(summary)
