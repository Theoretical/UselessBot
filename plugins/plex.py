from aiohttp import get, post
from json import dumps
from lxml.html import fromstring
from os import environ
from urllib.parse import quote
import plexapi
from plexapi.myplex import MyPlexUser as plex

async def invite_member(member):
    server_id = '503c85f2d47514dbfc3260c2a29ccb9cb113b071'
    account = plex.signin(environ.get('PLEX_EMAIL'), environ.get('PLEX_PASSWORD'))

    headers = plexapi.BASE_HEADERS
    headers['X-Plex-Token'] = account.authenticationToken
    print(account.authenticationToken)
    headers['Content-Type'] = 'application/json'
    data = {
        'server_id': server_id,
        'shared_server': {
            'library_section_ids': [],
            'invited_email': member
        },
        'shared_settings': []
    }

    res = await post('https://plex.tv/api/servers/%s/shared_servers' % server_id, headers=headers, data=dumps(data))
    data = await res.text()

def on_load(bot):
    print(environ.get('SB_API'))
    print(environ.get('CP_API'))


async def add_movie(bot, msg, msg_obj):
    url = 'http://127.0.0.1:5050/api/%s/movie.add?identifier=%s'

    imdb_id = 'tt' + msg[2].split('tt')[1]

    res = await get(url % (environ.get('CP_API'), imdb_id))
    data = await res.json()

    if not data['success']:
        await bot.send_message(msg_obj.channel, 'Failed to add movie :(')
        return True

    await get('http://127.0.0.1:5050/api/%s/movie.searcher.full_search' % environ.get('CP_API'))
    await bot.send_message(msg_obj.channel, '`Added movie: %s`' % data['movie']['title'])
    return True

async def add_show(bot, msg, msg_obj):
    url = 'http://127.0.0.1:8081/api/%s/' % environ.get('SB_API')

    if not str.isdigit(msg[2]):
        return await get_first(bot, msg, msg_obj)

    res = await get(url + '?cmd=show.addnew&tvdbid=%s&status=wanted&initial=fullhdtv|hdwebdl|fullhdwebdl|hdbluray|fullhdbluray' % msg[2])
    data = await res.json()
    await bot.send_message(msg_obj.channel, '`%s: %s`' % (data['result'], data['message']))

    return True


async def list_shows(bot, msg, msg_obj):
    url = 'http://127.0.0.1:8081/api/%s/' % environ.get('SB_API')

    res = await get(url + '?cmd=shows')
    data = await res.json()

    out_msg = '`'
    for show in data['data']:
        obj = data['data'][show]

        out_msg += '<%s> <%s quality> <%s>\n' % (obj['show_name'], obj['quality'], obj['status'])

    out_msg += '`\n'
    url = 'http://127.0.0.1:5050/api/%s/movie.list' % environ.get('CP_API')
    res = await get(url)
    data = await res.json()

    for movie in data['movies']:
        out_msg += '*<%s>*\n' % movie['title']

    await bot.send_message(msg_obj.channel, out_msg)
    return True

async def search(bot, msg, msg_obj):
    # Annoying...
    print(quote(' '.join(msg[2:])))
    url = 'http://thetvdb.com/api/GetSeries.php?seriesname=%s' % quote(' '.join(msg[2:]))

    res = await get(url)
    text = await res.text()
    node = fromstring('\n'.join(text.split('\n')[1:]))

    series = node.xpath('//series')
    out_msg = ''

    for s in series:
        name = s.xpath('./seriesname/text()')[0]
        id = s.xpath('./seriesid/text()')[0]
        year = s.xpath('./firstaired/text()')[0] if len(s.xpath('./firstaired/text()')) else 'N/A'
        network = s.xpath('./network/text()')[0] if len(s.xpath('./network/text()')) else 'N/A'

        out_msg += '<%s> <%s> <%s> ID: %s\n' % (name, year, network, id)

    await bot.send_message(msg_obj.channel, '`%s`' % out_msg)
    return True

async def get_first(bot, msg, msg_obj):
    url = 'http://thetvdb.com/api/GetSeries.php?seriesname=%s' % quote(' '.join(msg[2:]))

    res = await get(url)
    text = await res.text()
    node = fromstring('\n'.join(text.split('\n')[1:]))

    series = node.xpath('//seriesid')[0].text

    url = 'http://127.0.0.1:8081/api/%s/' % environ.get('SB_API')

    if not str.isdigit(series):
        return False

    res = await get(url + '?cmd=show.addnew&tvdbid=%s&status=wanted&initial=fullhdtv|hdwebdl|fullhdwebdl|hdbluray|fullhdbluray' % series)
    data = await res.json()
    await bot.send_message(msg_obj.channel, '`%s: %s`' % (data['result'], data['message']))

    return True

async def on_message(bot, msg, msg_obj):
    if msg[0] == 'plex':
        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['mod', 'admin']:
            return
        
        user = msg[1]

        if user == 'search':
            return await search(bot, msg, msg_obj)
        if user == 'add':
            if 'imdb' in msg[2] or 'tt' in msg[2]:
                return await add_movie(bot, msg, msg_obj)
            else:
                return await add_show(bot, msg, msg_obj)
        if user == 'list':
            return await list_shows(bot, msg, msg_obj)
        await invite_member(user)
        await bot.send_message(msg_obj.channel, '`Invited email to plex server!`')

        return True

