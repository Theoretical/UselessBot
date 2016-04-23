from aiohttp import post
from json import dumps
from os import environ
import plexapi
from plexapi.myplex import MyPlexUser as plex

async def invite_member(member):
    server_id = '616a9b7e25b6b9ab635b2bffdd0079f31cb7cb4a'
    account = plex.signin(environ.get('PLEX_EMAIL'), environ.get('PLEX_PASSWORD'))

    headers = plexapi.BASE_HEADERS
    headers['X-Plex-Token'] = account.authenticationToken
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
    pass

async def on_message(bot, msg, msg_obj):
    if msg[0] == 'plex':
        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['mod', 'admin']:
            return
        
        user = msg[1]
        await invite_member(user)
        await bot.send_message(msg_obj.channel, '`Invited: {} to plex server!`'.format(user))

        return True

