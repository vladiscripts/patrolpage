#!/usr/bin/env python3
# author: https://github.com/vladiscripts
import requests
import re
import pywikibot

namespaces_excluded = r'(?:Special|Служебная|Участник|User|У|U|Обсуждение[ _]участника|User talk|ОУ|Википедия|ВП|Обсуждение[ _]Википедии|Обсуждение):'
interwiki_prefix = r':?[a-z]+?:'
closing_tpls = re.compile(r'\{\{([Оо]тпатрулировано|[Пп]атр|[Сс]делано|[Dd]one|[Оо]тклонено)\s*(?:\|.*?)?\}\}')
sections_re = re.compile(r'\n={2,}[^=]+={2,}\n.*?(?=\n={2,}[^=]+={2,}\n|$)', flags=re.DOTALL)
clean_all_striked = re.compile(r'<s>.*?</s>', flags=re.DOTALL | re.I)  # Удаляем всё, что внутри <s> ... </s>
# link_not_striked_re = re.compile(r'\s*(?<!<s>)\s*(\[\[(?!%s)(?!%s).*?\]\])' % (interwiki_prefix, namespaces_excluded), flags=re.I)  # не зачёркнутая ссылка
link_title_re = re.compile(r'\[\[([^]|]+).*?\]\]')  # заголовок целевой страницы из ссылки
link_re = re.compile(r'\s*(\[\[(?!%s)(?!%s).*?\]\])' % (interwiki_prefix, namespaces_excluded), flags=re.I)

s = requests.Session()
s.headers = {'User-Agent': '[[w:ru:User:TextworkerBot]] / page revision checker'}


def get_pagesdata_from_api(titles: str | list):
    # https://ru.wikipedia.org/w/api.php?action=query&format=json&prop=flagged|info&utf8=1&titles=ЗАГЛАВИЕ  # или ЗАГЛАВИЕ1|ЗАГЛАВИЕ2
    titles = '|'.join(titles) if isinstance(titles, list) else [titles]
    params = {'action': 'query', 'prop': 'flagged|info', 'titles': titles, 'format': 'json', 'utf8': 1, }  # 'redirects': 1
    r = s.get(url='https://ru.wikipedia.org/w/api.php', params=params)
    j = r.json()['query'].get('pages').values()
    if not j:
        print("нет ['query']['pages'] в " + r.request.url)
        return None
    pages_info = {i['title']: i for i in j}
    return pages_info


def check_page_patrolled(p: dict) -> bool:
    """ API's doc: https://ru.wikipedia.org/w/api.php?action=help&modules=query%2Bflagged """
    if 'flagged' not in p or 'pending_since' in p['flagged']:
        # print('не патрулировано: ' + title)
        return False
    else:
        # print('патрулировано: ' + title)
        return True


def first_char_to_lowercase(text) -> str:
    return text[0].lower() + text[1:] if text else ''


def title_normalize(text) -> str:
    title = link_title_re.match(text).group(1).replace('_', ' ').strip()
    return title[0].upper() + title[1:] if title else ''


def get_links_not_striked(text) -> list[str]:
    text_cleaned = clean_all_striked.sub('', text)
    links = link_re.findall(text_cleaned)
    return links


def section_links_processing(d, section, redirects):
    """ Проверка ссылок в разделе, зачёркивание """
    wikilink_not_striked = get_links_not_striked(section)  # не зачёркнутые викиссылки
    if not wikilink_not_striked:
        return d, section, redirects
    titles = [title_normalize(link) for link in wikilink_not_striked]
    page_properties = get_pagesdata_from_api(titles)
    if not page_properties:
        return d, section, redirects

    for link in wikilink_not_striked:
        title = title_normalize(link)
        page_info = page_properties.get(title)
        if not page_info:
            print(f'не найден title "{title}" в page_properties')
            continue
        is_patrolled = check_page_patrolled(page_info)
        if is_patrolled:
            # ссылка отпатрулирована, зачёркиваем
            d.is_patrolled_page_found = True
            section = section.replace(link, '<s>%s</s>' % link)
        if 'redirect' in page_properties:
            # ссылка является перенаправлением
            redirects.add(title)
    return d, section, redirects


def section_closing(d, section, redirects):
    """ Установка шаблона {{отпатрулировано}} в раздел где все ссылки отпатрулированы """
    wikilink_not_striked = get_links_not_striked(section)
    if wikilink_not_striked:
        # есть не зачёркнутые (не отпатрулированные) викиссылки в разделе, ничего не делаем
        pass
    else:
        # все ссылки зачёркнуты (отпатрулированы), закрываем раздел
        section = section.rstrip()
        if not redirects:
            section = '%s\n: {{отпатрулировано}} участниками. --~~~~\n' % section
        else:
            section = '%s\n: {{отпатрулировано}} участниками. В запросе были перенаправления: %s. --~~~~\n' \
                      % (section, ', '.join(['[[%s]]' % t for t in redirects]))
        d.is_section_closed = True
    return d, section


class ForumPageChangedStatus:
    def __init__(self):
        self.is_patrolled_page_found = False
        self.is_section_closed = False


def main():
    # Параметр "user" нужен при наличии разноименных ботов на одном аккаунте tool.wmflab.org
    # В другом случае лучше его удалить
    site = pywikibot.Site('ru', 'wikipedia', user='TextworkerBot')
    workpages = ['Википедия:Запросы к патрулирующим',
                 'Википедия:Запросы к патрулирующим от автоподтверждённых участников']
    for workpage in workpages:
        # Загрузка страницы запросов
        page = pywikibot.Page(site, workpage)
        page_text = page.get()
        d = ForumPageChangedStatus()

        # Проверка разделов
        sections = [section for section in sections_re.findall(page_text)]
        for section in sections:
            if link_re.search(section):
                redirects = set()
                section_original = section
                d, section, redirects = section_links_processing(d, section, redirects)
                if not closing_tpls.search(section):
                    d, section = section_closing(d, section, redirects)
                page_text = page_text.replace(section_original, section)

        # Постинг
        if d.is_patrolled_page_found or d.is_section_closed:
            page.text = page_text
            summary = 'зачеркнуто отпатрулированное, автоитог' if d.is_section_closed else 'зачеркнуто отпатрулированное'
            page.save(summary)


def test():
    d = ForumPageChangedStatus()
    page_text = """
== <s>[[Когурё]]</s> ==

47 правок. Статья в кошмарном состоянии с кучей ОРИСС без источников. Подтвердите пожалуйста мои правки чтобы я могла продолжить чистить от ОРИСС.  [[У:Ulianurlanova|Ulianurlanova]] ([[ОУ:Ulianurlanova|обс.]]) 02:04, 19 января 2022 (UTC)
* {{Отказано}} Править можно и без подтверждения. А сейчас в статье куча проблем - такое не патрулируется. --[[У:EstherColeman|<span style="color:#000000;font-family:Segoe Script;">Esther Coleman</span>]] <sup>[[ОУ:EstherColeman|обс.]]</sup> 06:51, 19 января 2022 (UTC)

== [[День пожарной охраны России]] ==
22 правки. — [[Special:Contributions/2A00:1370:8186:BB3:A30C:5EA3:D6AA:40E6|2A00:1370:8186:BB3:A30C:5EA3:D6AA:40E6]] 21:07, 30 апреля 2025 (UTC)

== [[Без обид]] ==
2 правки. — [[Special:Contributions/2A02:2378:1192:85A8:0:0:0:1|2A02:2378:1192:85A8:0:0:0:1]] 16:42, 30 апреля 2025 (UTC)
* {{Отпатрулировано}}. [[У:Ochota ta Wola|Ochota ta Wola]] ([[ОУ:Ochota ta Wola|обс.]]) 16:49, 30 апреля 2025 (UTC)

== <s>[[Государственный переворот в Пруссии 1932 года]]</s> ==
Создал статьи "Боксгеймские документы" и "Государственный переворот в Пруссии 1932 года" по аналогии с англоязычными версиями статей, немало добавил от себя— == — [[У:IStorik1991|IStorik1991]] ([[ОУ:IStorik1991|обс.]]) 20:11, 29 апреля 2025 (UTC)
* {{Отпатрулировано}}. [[У:Ochota ta Wola|Ochota ta Wola]] ([[ОУ:Ochota ta Wola|обс.]]) 14:44, 30 апреля 2025 (UTC)
    """
    sections = [s for s in sections_re.findall(page_text)]
    for section in sections:
        if link_re.search(section):
            redirects = set()
            section_original = section
            d, section, redirects = section_links_processing(d, section, redirects)
            if not closing_tpls.search(section):
                d, section = section_closing(d, section, redirects)
            page_text = page_text.replace(section_original, section)
            pass
    pass


if __name__ == '__main__':
    main()
    # test()
