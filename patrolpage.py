#!/usr/bin/env python3
# author: https://github.com/vladiscripts
import requests
import re
import pywikibot

namespaces_excluded = r'(?:Special|Служебная|Участник|User|У|U|Обсуждение[ _]участника|User talk|ОУ|Википедия|ВП|Обсуждение[ _]Википедии|Обсуждение):'
closing_tpls = re.compile(r'\{\{([Оо]тпатрулировано|[Пп]атр|[Оо]тпат|[Сс]делано|[Dd]one|[Оо]тклонено)\s*(?:\|.*?)?\}\}')
sections_re = re.compile(r'\n={2,}[^=]+={2,}\n.*?(?=\n={2,}[^=]+={2,}\n|$)', flags=re.DOTALL)
clean_all_striked = re.compile(r'<s>.*?</s>', flags=re.DOTALL | re.I)  # Удаляем всё, что внутри <s> ... </s>
# link_not_striked_re = re.compile(r'\s*(?<!<s>)\s*(\[\[(?!%s)(?!%s).*?\]\])' % (interwiki_prefix, namespaces_excluded), flags=re.I)  # не зачёркнутая ссылка
link_title_re = re.compile(r'\[\[([^]|]+).*?\]\]')  # заголовок целевой страницы из ссылки
link_re = re.compile(r'\s*(\[\[(?!%s).*?\]\])' % namespaces_excluded, flags=re.I)


class ForumPageChangedStatus:
    def __init__(self):
        self.is_patrolled_page_found = False
        self.is_section_closed = False


s = requests.Session()
s.headers = {'User-Agent': '[[w:ru:User:TextworkerBot]] / page revision checker'}


def get_pagesdata_from_api(titles: list[str]) -> dict | None:
    """ https://ru.wikipedia.org/w/api.php?action=query&format=json&prop=flagged|info&utf8=1&titles=ЗАГЛАВИЕ  # или ЗАГЛАВИЕ1|ЗАГЛАВИЕ2 """
    params = {'action': 'query', 'prop': 'flagged|info', 'titles': '|'.join(titles), 'format': 'json', 'utf8': 1, }  # 'redirects': 1
    response = s.get(url='https://ru.wikipedia.org/w/api.php', params=params)
    query = response.json().get('query', {})
    if not query or 'interwiki' in query:
        print("нет ['query'] или есть 'interwiki' в " + response.request.url)
        return None
    pages = query.get('pages').values()
    if not pages:
        print("нет ['query']['pages'] в " + response.request.url)
        return None
    pages_info = {page['title']: page for page in pages}
    return pages_info


def is_page_patrolled(p: dict) -> bool:
    """ API's doc: https://ru.wikipedia.org/w/api.php?action=help&modules=query%2Bflagged """
    if 'flagged' not in p or 'pending_since' in p['flagged']:
        # print('не патрулировано: ' + title)
        return False
    else:
        # print('патрулировано: ' + title)
        return True


def title_normalize(text) -> str:
    title = link_title_re.match(text).group(1).replace('_', ' ').strip()
    return title[0].upper() + title[1:] if title else ''


def get_links_not_striked(text) -> list[str]:
    text_cleaned = clean_all_striked.sub('', text)
    links = link_re.findall(text_cleaned)
    return links


def section_links_processing(d: ForumPageChangedStatus, section: str, redirects: set) -> tuple[ForumPageChangedStatus, str, set]:
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
        if is_page_patrolled(page_info):
            # ссылка отпатрулирована, зачёркиваем
            d.is_patrolled_page_found = True
            section = section.replace(link, '<s>%s</s>' % link)
        if 'redirect' in page_info:
            # ссылка является перенаправлением
            redirects.add(title)
    return d, section, redirects


def section_closing(d: ForumPageChangedStatus, section: str, redirects: set) -> tuple[ForumPageChangedStatus, str]:
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


def main():
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


def _test():
    d = ForumPageChangedStatus()
    page_text = """
== [[Vogue: Глазами редактора]] ==
новая статья — [[У:AllaBuraya|AllaBuraya]] ([[ОУ:AllaBuraya|обс.]]) 14:59, 21 января 2026 (UTC)

== [[en:Vogue]] ==
интервики — [[У:Petsernik|Petsernik]] ([[ОУ:Petsernik|обс.]]) 14:59, 72 мартобря 2326 (UTC)
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
    # _test()
