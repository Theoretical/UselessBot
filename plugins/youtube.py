from aiohttp import get, post
from asyncio import Lock
from bs4 import BeautifulSoup
from datetime import timedelta
from os import listdir, unlink
from os.path import isfile
from sys import modules
from concurrent.futures import ThreadPoolExecutor
import functools
import youtube_dl


playlist = list()
volume = .05
channel = None

class Skip():
    def __init__(self):
        self.users = set()

    def add(self, user):
        self.users.add(user)

    @property
    def allowed(self):
        return len(self.users) > 1

    def reset(self):
        self.users.clear()

ytdl_format_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': "mp3",
    'outtmpl': '/tmp/%(id)s',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': False,
    'no_warnings': True,
    'prefer_insecure': True,
    'source_address': '0.0.0.0'

}

music_lock = Lock()
skip = Skip()

def on_load(bot):
    bot.music = dict(playlist=list(), player=None, paused=False, stopped=False, song=None)
    #bot.loop.create_task(playback_loop(bot))
    print('Loaded yt!')

def on_unload(bot):
    if bot.music['player']:
        bot.music['player'].stop()
    bot.music = dict(playlist=list(), player=None, paused=False, stopped=False, song=None)

def extract_info(bot, *args, **kwargs):
    thread_pool = ThreadPoolExecutor(max_workers=2)
    ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
    return bot.loop.run_in_executor(thread_pool, functools.partial(ytdl.extract_info, *args, **kwargs))

def play(bot):
    bot.loop.create_task(play_song(bot))

def progress(bot):
    return round(bot.music['player'].loops * 0.02)

def on_finished(bot):
    global skip
    music = bot.music
    try:
        unlink('/tmp/' + music['song']['id'])
    except:
        pass
    music['song'] = None
    skip = Skip()

    if not music['stopped']:
        play(bot)

async def play_song(bot):
    global music_lock, volume, channel
    music = bot.music

    if music['paused']:
        if music['player']:
            music['paused'] = False
            music['player'].resume()
        return

    with await music_lock:
        try:
            song = music['playlist'].pop(0)
        except:
            return

        song_obj = bot.voice.create_ffmpeg_player('/tmp/' + song['id'])
        song_obj.after = lambda: bot.loop.call_soon_threadsafe(on_finished, bot)
        song_obj.volume = volume
        if 'duration' not in song:
            song['duration'] = 0
        music['song'] = song
        music['player'] = song_obj
        p = str(timedelta(seconds=progress(bot)))
        await bot.send_message(channel, '**Now Playing: {} | Elapsed: {}** |`{} |` *{}*'.format(song['title'], p, str(timedelta(seconds=song['duration'])), song['webpage_url']))
        song_obj.start()

async def parse_playlist(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    page = await post(url, headers=headers)
    page = await page.text()
    soup = BeautifulSoup(page, 'html.parser')
    tags = soup.find_all("tr", class_="pl-video yt-uix-tile ")
    links = []
    for tag in tags:
        links.append("http://www.youtube.com/watch?v=" + tag['data-video-id'])
    return links if len(links) > 0 else False


async def do_callback(bot, msg, msg_obj):
    module = modules[__name__]
    cb = 'on_' + msg[0]

    if not hasattr(module, cb) and msg[0] != 'message':
        print('no callback. %s | %s' % (module, cb))
        return False

    await getattr(module, cb)(bot, msg, msg_obj)
    return True


async def on_np(bot, msg, msg_obj):
    if bot.music['song']:
        song = bot.music['song']
        p = str(timedelta(seconds=progress(bot)))
        await bot.send_message(msg_obj.channel, '**Now Playing: {} | Elapsed: {} | {}** *{}*'.format(song['title'], p, str(timedelta(seconds=song['duration'])), song['webpage_url']))


async def on_shuffle(bot, msg, msg_obj):
    from random import shuffle
    for i in range(0, 5):
        shuffle(bot.music['playlist'])

    await on_queue(bot, msg, msg_obj)

async def on_playlist(bot, msg, msg_obj):
    global channel
    music = bot.music
    playlist_name = 'playlists/%s.txt' % msg[1]
   

    if not bot.is_voice_connected():
        for member in bot.get_all_members():
            if member == msg_obj.author and member.voice_channel is not None:
                await bot.join_voice_channel(member.voice_channel)

    if msg[1] == 'list':
        playlists = [x.split('.')[0] for x in listdir('playlists/')]
        await bot.send_message(msg_obj.channel, 'Available playlists: `{}`'.format('|'.join(playlists)))
        return

    if msg[1] == 'update':
        playlists = [x.split('.')[0] for x in listdir('playlists/')]
        for f in playlists:
            content = open('playlists/%s.txt' % f, 'rt').read().split('\n')
            urls = await parse_playlist(content[0])
            new_file = open('playlists/%s.txt' % f, 'wt')
            new_file.write('%s\n' % content[0])
            for url in urls:
                new_file.write('%s\n' % url)
            new_file.close()
        return

    if len(msg) > 2:
        urls = await parse_playlist(msg[2])
        f = open(playlist_name, 'wt')
        f.write('%s\n' % msg[2])
        for url in urls:
            f.write('%s\n' % url)
        f.close()

    if not isfile(playlist_name):
        await bot.send_messagE(msg_obj.channel, 'Invalid playlist name specified')
        return

    if msg_obj.channel.name != 'bot':
        for ch in bot.get_all_channels():
            if ch.name == 'bot':
                channel = ch
    else:
        channel = msg_obj.channel
    items = open(playlist_name, 'rt').read().split('\n')

    for num, item in enumerate(items[1:]):
        print('%s/%s' % (num, len(items[1:])))

        if num > 0 and not music['song']:
            play(bot)

        try:
            x = await extract_info(bot, url=item, download=True)
            if x is None:
                continue
        except:
            continue

        music['playlist'].append(x)

    if not music['song']:
        play(bot)
    await on_queue(bot, msg, msg_obj)

async def on_play(bot, msg, msg_obj):
    global channel
    music = bot.music

    if not bot.is_voice_connected():
        for member in bot.get_all_members():
            if member == msg_obj.author and member.voice_channel is not None:
                await bot.join_voice_channel(member.voice_channel)


    if msg_obj.channel.name != 'bot':
        for ch in bot.get_all_channels():
            if ch.name == 'bot' and ch.server == msg_obj.server:
                channel = ch

    else:
        channel = msg_obj.channel
    if len(bot.music['playlist']) > 0:
        queue_str = ''
        for song in music['playlist']:
            queue_str += '%s: (%s).\n' % (song['title'], str(timedelta(seconds=song['duration'])))

        p = str(timedelta(seconds=progress(bot)))
        total_len = sum([x['duration'] for x in music['playlist']])

        if music['song']:
            await bot.send_message(msg_obj.channel, '**Current queue length: {} | Current Song Elapsed: {}/{}** | `Songs: {}\nQueue: {}`'.format(str(timedelta(seconds=total_len)), p, str(timedelta(seconds=music['song']['duration'])), len(music['playlist']), queue_str))


    if 'playlist' not in msg[1]:
        music['playlist'].append(await extract_info(bot, url=msg[1], download=True))

        if not music['song']:
            play(bot)
        return

    items = await parse_playlist(msg[1])

    if not len(items):
        await bot.send_message(msg_obj.channel, 'Unable to download playlist!')
        return

    for num, item in enumerate(items):
        print('%s/%s' % (num, len(items)))

        if num > 0 and not music['song']:
            play(bot)

        try:
            x = await extract_info(bot, url=item, download=True)
        except:
            continue

        music['playlist'].append(x)

    if not music['song']:
        play(bot)
    await on_queue(bot, msg, msg_obj)

async def on_pause(bot, msg, msg_obj):
    if not bot.music['player']:
        return

    bot.music['paused'] = True
    bot.music['player'].pause()

async def on_resume(bot, msg, msg_obj):
    if bot.music['paused']:
        bot.music['paused'] = False
        bot.music['player'].resume()

async def on_volume(bot, msg, msg_obj):
    global volume
    
    if bot.permissions.get(msg_obj.author.id) not in ['user', 'mod', 'admin']:
        return
    
    if not str.isdigit(msg[1]) and int(msg[1]) < 60:
        return

    volume = int(msg[1]) / 100
    if bot.music['player']:
        bot.music['player'].volume = volume

    await bot.send_message(msg_obj.channel, '`{} set volume to: {}`'.format(msg_obj.author, volume))

async def on_skip(bot, msg, msg_obj):
    global skip
    skip.add(msg_obj.author)

    level = bot.permissions.get(msg_obj.author.id)

    if (bot.music['player'] and level in ['mod', 'admin']) or skip.allowed: #TODO: Permissions.
        bot.music['player'].stop()
        bot.music['player'] = None
        return

    await bot.send_message(msg_obj.channel, '`{} Started a skip request! Need 1 more person to request a skip to continue!`'.format(msg_obj.author))

async def on_queue(bot, msg, msg_obj):
    music = bot.music
    queue_str = ''
    for song in music['playlist'][:20]:
        queue_str += '%s: (%s).\n' % (song['title'], str(timedelta(seconds=song['duration'])))

    p = str(timedelta(seconds=progress(bot)))
    total_len = sum([x['duration'] for x in music['playlist']])

    if music['song']:
        await bot.send_message(msg_obj.channel, '**Current queue length: {} | Current Song Elapsed: {}/{} **| `Songs: {}\nQueue: {}`'.format(str(timedelta(seconds=total_len)), p, str(timedelta(seconds=music['song']['duration'])), len(music['playlist']), queue_str))

async def on_summon(bot, msg, msg_obj):
    level = bot.permissions.get(msg_obj.author.id)

    if level is None or level not in ['user', 'mod', 'admin']:
        return

    if not bot.voice:
        for member in bot.get_all_members():
           if member == msg_obj.author and member.voice_channel is not None:
                await bot.join_voice_channel(member.voice_channel)
                return
    else:
        for bots in bot.get_all_members():
            if bots == bot.user and bots.server == msg_obj.server:
                for member in bot.get_all_members():
                    if member == msg_obj.author and member.voice_channel is not None:
                        print('Moving: %s to %s' % (bots, member.voice_channel))
                        await bot.move_member(bots, member.voice_channel)
                        print('Moving: %s to %s' % (bots, member.voice_channel))
                        return

async def on_move(bot, msg, msg_obj):
    level = bot.permissions.get(msg_obj.author.id)

    if level is None or level not in ['admin']:
        return

    for bots in bot.get_all_members():
        if bots == bot.user and bots.server == msg_obj.server:
            for channel in bot.get_all_channels():
                if msg_obj.server.id  == channel.server.id and channel.name.lower() == msg[1].lower():
                    print ('Moving bot to: %s/%s' % (channel, msg[1]))
                    await bot.move_member(bots, channel)
                    return

async def on_message(bot, msg, msg_obj):
    print('%s: %s' % (msg_obj.author.id, msg_obj.content))
    return await do_callback(bot, msg, msg_obj)
