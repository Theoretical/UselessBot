from aiohttp import get, post, head
from lxml.html import fromstring
from urllib.parse import quote

def on_load(bot):
    pass


async def get_animelist(title):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    res = await get('http://myanimelist.net/search/prefix.json?type=all&keyword=%s&v=1' % title, headers=headers)
    data = await res.json()

    return data['categories'][0]['items'][0]['url']

async def parse_anime(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    res = await get(url, headers=headers)
    data = await res.text()

    nodes = fromstring(data)
    
    info = dict()
    info['score'] = nodes.xpath('//div[contains(@class, "score")]/text()')[0].strip()
    info['rank'] = nodes.xpath('//span[contains(@class,"numbers")]/strong/text()')[0]
    info['img'] = nodes.xpath('//img[@itemprop="image"]')[0].get('src')
    info['name'] = nodes.xpath('//span[@itemprop="name"]/text()')[0]
    info['synopsis'] = nodes.xpath('//span[@itemprop="description"]/text()')[0]

    info['cr'] = 'https://www.crunchyroll.com/%s' % info['name'].lower().replace(' ', '-')

    cr_res = await get(info['cr'], headers=headers)
    if cr_res.status != 200:
        info['cr'] = 'N/A'

    info['kiss'] = 'https://kissanime.to/Anime/%s'% info['name'].replace(' ', '-')
    return info



async def on_message(bot, msg, msg_obj):

    if msg[0] == 'anime':
        title = quote(' '.join(msg[1:]))
        url = await get_animelist(title)
        anime = await parse_anime(url)

        await bot.send_message(msg_obj.channel, '**%s** | _%s_\n*Ranked*: **%s** | *Score*: **%s**\nCR Stream: %s | Kiss(WIP): %s\n\n`%s`' % (anime['name'], url, anime['rank'], anime['score'], anime['cr'], anime['kiss'], anime['synopsis']))
        return True
    return False
