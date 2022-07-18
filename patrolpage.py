#!/usr/bin/env python3
# author: https://github.com/vladiscripts
#
# API's doc: https://ru.wikipedia.org/w/api.php?action=help&modules=query%2Bflagged
import requests
import re
import pywikibot

namespaces_excluded = r'(?:Special|Служебная|Участник|User|У|U|Обсуждение[ _]участника|ОУ|Википедия|ВП|Обсуждение[ _]Википедии|Обсуждение):'
closing_tpls = re.compile(r'\{\{([Оо]тпатрулировано|[Сс]делано|[Dd]one|[Оо]тклонено)\s*(?:\|.*?)?\}\}')
sections_re = re.compile(r'\n={2,}[^=]+={2,}\n.*?(?=\n={2,}[^=]+={2,}\n|$)', flags=re.DOTALL)
link_not_striked_re = re.compile(r'\s*(?<!<s>)\s*(\[\[(?!%s).*?\]\])' % namespaces_excluded, flags=re.I)  # не зачёркнутая ссылка
link_title_re = re.compile(r'\[\[([^]|]+).*?\]\]')  # заголовок целевой страницы из ссылки
link_re = re.compile(r'\s*(\[\[(?!%s).*?\]\])' % namespaces_excluded)


def get_pagedata_from_api(title):
    # https://ru.wikipedia.org/w/api.php?action=query&format=json&prop=flagged|info&utf8=1&titles=ЗАГЛАВИЕ_СТРАНИЦЫ
    params = {'action': 'query', 'prop': 'flagged|info', 'titles': title,
              'format': 'json', 'utf8': 1, }  # 'redirects': 1
    r = requests.get(url='https://ru.wikipedia.org/w/api.php', params=params)
    for page_info in r.json()['query']['pages'].values():
        return page_info


def check_page_patrolled(p):
    if not 'flagged' in p or 'pending_since' in p['flagged']:
        # print('не патрулировано: ' + title)
        return False
    else:
        # print('патрулировано: ' + title)
        return True


def links_processing(d, section, redirects):
    """ Проверка ссылок в разделе, зачёркивание """
    wikilink_not_striked = link_not_striked_re.findall(section)  # не зачёркнутые викиссылки
    for link in wikilink_not_striked:
        title = link_title_re.match(link).group(1)
        page_properties = get_pagedata_from_api(title)
        is_patrolled = check_page_patrolled(page_properties)
        if is_patrolled:
            # ссылка отпатрулирована, зачёркиваем
            d.patrolled_page_found = True
            section = section.replace(link, '<s>%s</s>' % link)
        if 'redirect' in page_properties:
            # ссылка является перенаправлением
            redirects.add(title)
    return d, section, redirects


def section_closing(d, section, redirects):
    """ Закрытие разделов с отработанными запросами """
    wikilink_not_striked = link_not_striked_re.findall(section)
    if wikilink_not_striked:
        # есть не зачёркнутые (не отпатрулированные) викиссылки в разделе, ничего не делаем
        pass
    else:
        # все ссылки зачёркнуты (отпатрулированы), закрываем раздел
        section = section.rstrip()
        if not redirects:
            section = '%s\n: {{отпатрулировано}} участниками. --~~~~\n' % section
        else:
            redirects_list = ', '.join(['[[%s]]' % t for t in redirects])
            section = '%s\n: {{отпатрулировано}} участниками. В запросе были перенаправления: %s. --~~~~\n' \
                      % (section, redirects_list)
        d.section_closed = True
    return d, section


class PageData:
    def __init__(self):
        self.patrolled_page_found = False
        self.section_closed = False


def main():
    # Параметр "user" нужен при наличии разноименных ботов на одном аккаунте tool.wmflab.org
    # В другом случае лучше его удалить
    site = pywikibot.Site('ru', 'wikipedia', user='TextworkerBot')
    workpages = ['Википедия:Запросы к патрулирующим',
                 'Википедия:Запросы к патрулирующим от автоподтверждённых участников']
    for workpage in workpages:
        page = pywikibot.Page(site, workpage)
        page_text = page.get()
        d = PageData()

        # Проверка разделов
        sections = [section for section in sections_re.findall(page_text)]
        for section in sections:
            if link_re.search(section) and not closing_tpls.search(section):
                redirects = set()
                section_original = section
                d, section, redirects = links_processing(d, section, redirects)
                d, section = section_closing(d, section, redirects)
                page_text = page_text.replace(section_original, section)

        # Постинг
        if d.patrolled_page_found or d.section_closed:
            page.text = page_text
            summary = 'зачеркнуто отпатрулированное, автоитог' if d.section_closed else 'зачеркнуто отпатрулированное'
            page.save(summary)


def test():
    d = PageData()
    page_text = """
== <s>[[Когурё]]</s> ==

47 правок. Статья в кошмарном состоянии с кучей ОРИСС без источников. Подтвердите пожалуйста мои правки чтобы я могла продолжить чистить от ОРИСС.  [[У:Ulianurlanova|Ulianurlanova]] ([[ОУ:Ulianurlanova|обс.]]) 02:04, 19 января 2022 (UTC)
* {{Отказано}} Править можно и без подтверждения. А сейчас в статье куча проблем - такое не патрулируется. --[[У:EstherColeman|<span style="color:#000000;font-family:Segoe Script;">Esther Coleman</span>]] <sup>[[ОУ:EstherColeman|обс.]]</sup> 06:51, 19 января 2022 (UTC)  
    """
    sections = [s for s in sections_re.findall(page_text)]
    for section in sections:
        if link_re.search(section) and not closing_tpls.search(section):
            redirects = set()
            section_original = section
            d, section, redirects = links_processing(d, section, redirects)
            d, section = section_closing(d, section, redirects)
            page_text = page_text.replace(section_original, section)
            pass
    pass


if __name__ == '__main__':
    main()
    # test()
