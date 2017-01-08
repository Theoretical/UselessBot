from aiohttp import get
from asyncio import Lock, gather
from datetime import timedelta
from lxml.html import fromstring
from os import listdir, unlink, environ
from os.path import isfile
from random import shuffle
from time import time
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
import functools
import youtube_dl
import discord.utils
from spotipy import Spotify
from spotipy.util import prompt_for_user_token


class Skip:
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


def on_load(bot):
    bot.yt = dict()
    print('Loaded yt!')

async def on_unload(bot):
    for yt in bot.yt.values():
        await yt.quit()
    bot.yt = dict()


async def search_youtube(title):
    print('https://www.googleapis.com/youtube/v3/search?part=id,snippet&q=%s&key=%s' % (quote(title), environ['YT_KEY']))
    page = await get('https://www.googleapis.com/youtube/v3/search?part=id,snippet&q=%s&key=%s' % (quote(title), environ['YT_KEY']))
    data = await page.json()

    # We're going to try to isolate these to better videos..
    videos = [x['id']['videoId'] for x in data['items'] if 'videoId' in x['id']]

    page = await get('https://www.googleapis.com/youtube/v3/videos?part=id,snippet,contentDetails,status&id=%s&key=%s' % (','.join(videos), environ['YT_KEY']))
    print('https://www.googleapis.com/youtube/v3/videos?part=id,snippet,contentDetails,status&id=%s&key=%s' % (','.join(videos), environ['YT_KEY']))
    data = await page.json()
    video_id = None

    for item in data['items']:
        details = item['contentDetails']
        blocked = details.get('regionRestriction', {}).get('blocked', [])
        allowed = details.get('regionRestriction', {}).get('allowed', [])
        if 'CA' in blocked or (len(allowed) and 'CA' not in allowed) or details['definition'] != 'hd':
            continue
        video_id = item['id']

    if video_id is None:
        # default to vevo..
        for item in data['items']:
            if 'vevo' in item['snippet']['channelTitle'].lower():
                video_id = item['id']
                break

    if video_id is None and len(videos):
        # oh well...
        video_id = videos[0]

    if video_id:
        return 'https://youtube.com/watch?v=%s' % video_id

    return None

async def get_spotify_playlist(url):
    # Url can be a spotify url or uri.
    user = ''
    playlist_id = ''
    songs = []

    token = prompt_for_user_token('mdeception', 'user-library-read')

    spotify = Spotify(auth=token)
    if not 'http' in url:
        user = url.split('user:')[1].split(':')[0]
        playlist_id = url.split(':')[-1]
    else:
        user = url.split('user/')[1].split('/')[0]
        playlist_id = url.split('/')[-1]

    playlist = spotify.user_playlist(user, playlist_id, fields='tracks, next, name')

    tracks = playlist['tracks']
    for t in tracks['items']:
        track = t['track']
        songs.append('%s %s' % (track['name'], ' & '.join(x['name'] for x in track['artists'])))

    while tracks['next']:
        tracks = spotify.next(tracks)
        for t in tracks['items']:
            track = t['track']
            songs.append('%s %s' % (track['name'], ' & '.join(x['name'] for x in track['artists'])))

    return (playlist['name'], user, songs)

class YoutubePlayer:
    def __init__(self, bot, channel):
        self.playlist = list()
        self.music_lock = Lock()
        self.skip = Skip()
        self.bot = bot
        self.ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
        self.player = None
        self.song = None
        self.stopped = False
        self.paused = False
        self.voice = None
        self.channel = channel
        self.volume = .05

    def search_youtube(self, title):
        thread_pool = ThreadPoolExecutor(max_workers=4)
        return self.bot.loop.run_in_executor(thread_pool, search_youtube, title)

    def extract_info(self, *args, **kwargs):
        thread_pool = ThreadPoolExecutor(max_workers=2)
        return self.bot.loop.run_in_executor(thread_pool, functools.partial(self.ytdl.extract_info, *args, **kwargs))

    def process_info(self, item):
        thread_pool =ThreadPoolExecutor(max_workers=2)
        return self.bot.loop.run_in_executor(thread_pool, functools.partial(self.ytdl.process_ie_result, item, download=True))

    @property
    def progress(self):
        return round(self.player.loops * 0.02) if self.player else 0

    def play(self):
        self.bot.loop.create_task(self.play_song())

    def on_finished(self):
        try:
            unlink('/tmp/' + self.song['id'])
        except:
            pass

        self.song = None
        self.skip = Skip()

        if not self.stopped:
            self.play()

    async def play_song(self):
        if self.paused:
            if self.player:
                self.paused = False
                self.player.resume()


        if not self.bot.is_voice_connected(self.channel.server):
            # default to AFK channel..
            channel = discord.utils.get(self.channel.server.channels, name='AFK')
            self.voice = await self.bot.join_voice_channel(self.voice_channel or channel)
            self.voice_channel = channel.voice_channel

        with await self.music_lock:
            try:
                self.song = self.playlist.pop(0)
            except:
                return

            self.player = self.voice.create_ffmpeg_player('/tmp/' + self.song['id'], use_avconv=True)
            self.player.loops = 0 #???
            self.player.after = lambda: self.bot.loop.call_soon_threadsafe(self.on_finished)
            await self.send_np(self.channel)

            self.player.start()
            self.player.volume = self.volume

    async def quit(self):
        if self.player:
            self.player.stop()
        if self.voice:
            await self.voice.disconnect()

    async def process_commands(self, msg, msg_obj):
        callback_func = 'on_' + msg[0]

        if hasattr(self, callback_func):
            await getattr(self, callback_func)(msg, msg_obj)
            return True
        return False

    async def send_np(self, channel):
        if self.song:
            song = self.song
            position = str(timedelta(seconds=self.progress))
            length = str(timedelta(seconds=song.get('duration', 0)))
            await self.bot.send_message(channel, '```Now Playing: {0} requested by {1} | Timestamp: {2} | Length: {3}\n{4}```'.format(song['title'], song['requestor'], position, length, song['webpage_url']))


    async def join_default_channel(self, member):
        if self.voice:
            return

        old_voice = self.bot.is_voice_connected(member.server)
        if old_voice:
            self.voice = old_voice
            return

        default_name = 'AFK'
        channel = discord.utils.find(lambda m: m.id == member.id and m.server.id == member.server.id and m.voice_channel is not None, member.server.members)

        if channel is not None:
            self.voice = await self.bot.join_voice_channel(channel.voice_channel)
            self.voice_channel = channel.voice_channel
            return

        channel = discord.utils.get(member.server.channels, name=default_name)
        self.voice = await self.bot.join_voice_channel(channel)
        self.voice_channel = channel


    async def on_spotify(self, msg, msg_obj):
        t = time()
        playlist, user, songs = await get_spotify_playlist(msg[1])
        yt_search = gather(*(search_youtube(song) for song in songs))
        yt_songs = await yt_search
        yt_songs = [song for song in yt_songs if song is not None]

        ended = time()
        total_songs = len(songs)
        await self.bot.send_message(msg_obj.channel, '`Found: %s songs in playlist: %s by %s in %s seconds.!`' % (total_songs, playlist, user, ended - t))
        await self.join_default_channel(msg_obj.author)

        # Find a bot channel if we have one...
        if msg_obj.channel.name != 'bot':
            for ch in msg_obj.server.channels:
                if ch.name == 'bot':
                    self.channel = ch
                    break
        else:
            self.channel = msg_obj.channel

        playlist_task = gather(*(self.extract_info(url=item, download=True) for item in yt_songs))
        playlist = await playlist_task
        playlist = [x for x in playlist if x]
        for s in playlist:
            s['requestor'] = msg_obj.author.name

        self.playlist.extend(playlist)
        if not self.song:
            self.play()
        await self.on_queue(msg, msg_obj)
        return True

    async def on_np(self, msg, msg_obj):
        await self.send_np(msg_obj.channel)
        return True

    async def on_shuffle(self, msg, msg_obj):
        for i in range(0, 5):
            shuffle(self.playlist)

        await self.on_queue(msg, msg_obj)

    async def on_queue(self, msg, msg_obj):
        if self.song is None:
            return True

        queue_str = ''
        for song in self.playlist[:15]:
            queue_str += '%s: (%ss). requested by: %s\n' % (song['title'], str(timedelta(seconds=song['duration'])), song['requestor'])

        position = str(timedelta(seconds=self.progress))
        length = str(timedelta(seconds=self.song.get('duration', 0)))
        total_len = sum([x.get('duration', 0) for x in self.playlist])
        await self.bot.send_message(msg_obj.channel, '```Queue length: {} | Queue Size: {} | Current Song Progress: {}/{}\n{}```'.format(str(timedelta(seconds=total_len)), len(self.playlist), position, length, queue_str))


    async def on_play(self, msg, msg_obj):
        await self.join_default_channel(msg_obj.author)

        # Find a bot channel if we have one...
        if msg_obj.channel.name != 'bot':
            for ch in msg_obj.server.channels:
                if ch.name == 'bot':
                    self.channel = ch
                    break
        else:
            self.channel = msg_obj.channel

        if 'playlist' not in msg[1]:
            song = await self.extract_info(url=msg[1], download=True)
            song['requestor'] = msg_obj.author.name
            self.playlist.append(song)

        else:
            items = await self.extract_info(url=msg[1], process=False, download=False)
            playlist_task = gather(*(self.process_info(item) for item in items['entries']))
            playlist = await playlist_task
            playlist = [x for x in playlist if x]
            await self.bot.send_message(msg_obj.channel, '```Loaded: %s songs in %s seconds.```' % (len(playlist), end - t))
            if msg[-1] == 'shuffle':
                for i in range(0, 5):
                    shuffle(playlist)
            for song in playlist:
                song['requestor'] = msg_obj.author.name

            self.playlist.extend(playlist)

        if not self.song:
            self.play()

        if len(self.playlist) > 1:
            await self.on_queue(msg, msg_obj)

    async def on_pause(self, msg, msg_obj):
        if not self.player:
            return

        self.paused = True
        self.player.pause()

    async def on_resume(self, msg, msg_obj):
        if self.paused:
            self.paused = False
            self.player.resume()

    async def on_volume(self, msg, msg_obj):
        if self.bot.permissions.get(msg_obj.author.id) not in ['user', 'mod', 'admin']:
            return

        if len(msg) == 1:
            await self.bot.send_message(msg_obj.channel, '`Current Volume: %s`' % self.volume)
        else:
            if not str.isdigit(msg[1]): return
            self.volume = int(msg[1]) / 100

            if self.player:
                self.player.volume = self.volume

            await self.bot.send_message(msg_obj.channel, '`{} set the volume to {}`'.format(msg_obj.author, self.volume))

    async def on_skip(self, msg, msg_obj):
        self.skip.add(msg_obj.author)

        level = self.bot.permissions.get(msg_obj.author.id)

        if (self.player and level in ['mod', 'admin']) or self.skip.allowed:
            self.player.stop()
            self.player = None
            return True

        await self.bot.send_message(msg_obj.channel, '`{} Started a skip request! Need 1 more person to request a skip to continue!`'.format(msg_obj.author))

    async def on_summon(self, msg, msg_obj):
        if len(msg) > 1:
            member = discord.utils.find(lambda m: m.mention == msg[1], msg_obj.server.members)
        else:
            member  = msg_obj.author

        channel = discord.utils.find(lambda m: m.id == member.id and m.server.id == member.server.id and m.voice_channel is not None, member.server.members)
        self.voice = await self.bot.join_voice_channel(self.voice_channel or channel)
        self.voice_channel = channel.voice_channel

        await self.bot.send_message(msg_obj.channel, '`Joining channel with {}`'.format(member.mention))


async def on_message(bot, msg, msg_obj):
    if msg_obj.server not in bot.yt:
        bot.yt[msg_obj.server] = YoutubePlayer(bot, msg_obj.channel)

    return await bot.yt[msg_obj.server].process_commands(msg, msg_obj)
