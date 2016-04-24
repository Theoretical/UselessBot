from aiohttp import get, post
from json import dumps
from lxml.html import fromstring
from os import environ
from urllib.parse import quote
import plexapi
from plexapi.myplex import MyPlexUser as plex

async def invite_member(member):
    server_id = '616a9b7e25b6b9ab635b2bffdd0079f31cb7cb4a'
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
    pass


async def add_show(bot, msg, msg_obj):
    url = 'http://127.0.0.1:8081/api/%s/' % environ.get('SB_API')

    if not str.isdigit(msg[2]):
        return False

    res = await get(url + '?cmd=show.addnew&tvdbid=%s&status=wanted&initial=fullhdtv|hdwebdl|fullhdwebdl|hdbluray|fullhdbluray' % msg[2])
    data = await res.json()
    await bot.send_message(msg_obj.channel, '`%s: %s`' % (data['result'], data['message']))

    return True


async def list_shows(bot, msg, msg_obj):
    url = 'http://127.0.0.1:8081/api/%s/' % environ.get('SB_API')

    res = await get(url + '?cmd=shows')
    data = await res.json()

    out_msg = ''
    for show in data['data']:
        obj = data['data'][show]

        out_msg += '<%s> <%s quality> <%s>\n' % (obj['show_name'], obj['quality'], obj['status'])

    await bot.send_message(msg_obj.channel, '`%s`' % out_msg)
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
        year = s.xpath('./firstaired/text()')[0]
        network = s.xpath('./network/text()')[0] if len(s.xpath('./network/text()')) else 'N/A'

        out_msg += '<%s> <%s> <%s> ID: %s\n' % (name, year, network, id)

    await bot.send_message(msg_obj.channel, '`%s`' % out_msg)
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
            return await add_show(bot, msg, msg_obj)
        if user == 'list':
            return await list_shows(bot, msg, msg_obj)
        await invite_member(user)
        await bot.send_message(msg_obj.channel, '`Invited: {} to plex server!`'.format(user))

        return True

