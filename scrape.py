import re
from urllib.parse import urlparse

from enum import Enum

from urllib.parse import urlparse, parse_qs
from lxml.html import fromstring, HtmlElement
from requests import get
from bs4 import BeautifulSoup


class SearchEngine(Enum):
    GOOGLE = 1


def search_engine_to_url(engine: SearchEngine):
    url = "https://www."

    if engine == SearchEngine.GOOGLE:
        url += "google.com/search?q="

    return url

def stringify_children(node):
    from lxml.etree import tostring
    from itertools import chain
    return ''.join(
        chunk for chunk in chain(
            (node.text,),
            chain(*((tostring(child, with_tail=False), child.tail) for child in node.getchildren())),
            (node.tail,)) if chunk)

def get_top_search(prompt: str, search_engine: SearchEngine = SearchEngine.GOOGLE, max_sentences: int = 2):
    search_url = search_engine_to_url(search_engine)

    raw = get(search_url + prompt).text
    page = fromstring(raw)

    urls = []
    for result in page.cssselect("h3"):
        # result is an html.lxml.HtmlElement
        result: HtmlElement

        #link = result.getparent().getparent().getparent()
        link = result
        no_result = False

        while True:
            link = link.getparent()

            if link is None: # we reached the top of the page
                no_result = True
                break

            if link.tag == "a": # It's a link!
                break

        if no_result:
            continue

        """for c in link.getchildren():
            inspect(c)"""

        url = link.get("href")
        if url.startswith("/url?"):
            url = parse_qs(urlparse(url).query)['q']
            
        if type(url) != str:
            urls.append(url[0])

    if len(urls) < 1: # We didn't get any search results
        return None


    #results = []
    #for i in range(len(urls)):
    top_result = urls[0]

    try:
        top_result_raw = get(top_result).text
    except:
        return "Sorry, I had a problem searching for that. Please try again later."

    soup = BeautifulSoup(top_result_raw, "lxml")

    allowlist = [
        'p',
        'b'
    ]
    text_elements = [t for t in soup.find_all(text=True) if t.parent.name in allowlist or t.parent.parent and t.parent.parent.name in allowlist]
    text_elements = ''.join(text_elements)

    #all_text = soup.find('p').getText()
    """all_text = all_text.get_text(' ', strip=True)"""

    # limit to a number of sentences
    capped_text = ' '.join(re.split(r'(?<=[.?!])\s+', text_elements, max_sentences)[:-1])

    domain_name = urlparse(top_result).netloc
    final_result = f"From {domain_name}, {capped_text}"

    return final_result