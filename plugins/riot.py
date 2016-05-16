from aiohttp import get
from cassiopeia import riotapi
from cassiopeia.type.core.common import LoadPolicy
from lxml.html import fromstring
from os import environ

def on_load(bot):
    riotapi.set_region("NA")
    riotapi.print_calls(False)
    riotapi.set_api_key(environ.get("RIOT_API"))
    riotapi.set_load_policy(LoadPolicy.lazy)

async def get_mmr(summoner):
    res = await get('http://na.op.gg/summoner/ajax/mmr/summonerName=%s' % summoner, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36'})
    data = await res.text()
    open('r.txt', 'wt').write(data)
    print(data)
    nodes = fromstring(data)

    mmr = dict()
    mmr['value'] = nodes.xpath('//div[@class="MMR"]/text()')[0].strip()
    mmr['tip'] = nodes.xpath('//div[contains(@class, "TipStatus")]/text()')[0]
    mmr['average'] = nodes.xpath('//span[@class="InlineMiddle"]/text()')[0].strip()

    return mmr


async def on_message(bot, msg, msg_obj):
    if msg[0] == 'summoner':
        summoner = riotapi.get_summoner_by_name(' '.join(msg[1:]))
        print(summoner)
        match_list = summoner.match_list()
        first = match_list[0].match()

        player = first.participants[summoner]

        await bot.send_message(msg_obj.channel, '%s %s his last game in %s lane, role: %s.\nChampion: %s | Kills: %s | Deaths: %s | Assists: %s | CS: %s | KDA: %s\nBans: %s' % (msg[1],  "won" if player.stats.win else "lost", player.timeline.lane, player.timeline.role, player.champion.name, player.stats.kills, player.stats.deaths, player.stats.assists, player.stats.cs, player.stats.kda, 
            ('/'.join([ban.champion.name for ban in first.red_team.bans + first.blue_team.bans]))))
        return True


    if msg[0] == 'master':
        master = [entry.summoner for entry in riotapi.get_master()]

        for summoner in master:
            if master.name.lower() == ' '.join(msg[1:]).lower():
                await bot.send_message(msg_obj.channel, '**YOU THINK THAT NIGGA IS A JOKE?**')

        await bot.send_message(msg_obj.channel, 'No, that nigga is basically johnny...')
        return True

    if msg[0] == 'mmr':
        summoner = ''.join(msg[1:])

        mmr = await get_mmr(summoner)
        await bot.send_message(msg_obj.channel, '**%s** has an MMR of: *%s*\n%s\n`%s`' % (summoner, mmr['value'], mmr['tip'], mmr['average']))
        return True
