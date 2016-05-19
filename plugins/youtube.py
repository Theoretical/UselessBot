from asyncio import Lock
from datetime import timedelta
from os import listdir, unlink
from os.path import isfile
from random import shuffle
from concurrent.futures import ThreadPoolExecutor
import functools
import youtube_dl

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
        self.volume = .4

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

        with await self.music_lock:
            try:
                self.song = self.playlist.pop(0)
            except:
                return

            self.player = self.voice.create_ffmpeg_player('/tmp/' + self.song['id'])
            self.player.loops = 0 #???
            self.player.after = lambda: self.bot.loop.call_soon_threadsafe(self.on_finished)
            self.player.volume = self.volume
            await self.send_np(self.channel)

            self.player.start()

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
            length = str(timedelta(seconds=song['duration']))
            await self.bot.send_message(channel, '```Now Playing: {0} requested by {1} | Timestamp: {2} | Length: {3}\n{4}```'.format(song['title'], song['requestor'], position, length, song['webpage_url']))

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
        length = str(timedelta(seconds=self.song['duration']))
        total_len = sum([x['duration'] for x in self.playlist])
        await self.bot.send_message(msg_obj.channel, '```Queue length: {} | Queue Size: {} Current Song Progress: {}/{}\n{}```'.format(str(timedelta(seconds=total_len)), len(self.playlist), position, length, queue_str))


    async def on_playlist(self, msg, msg_obj):
        playlist_name = 'playlists/%s.txt' % msg[1]

        if self.voice is None:
            for member in self.bot.get_all_members():
                if member == msg_obj.author and member.voice_channel is not None:
                    self.voice = await self.bot.join_voice_channel(member.voice_channel)

        # Find a bot channel if we have one...
        if msg_obj.channel.name != 'bot':
            for ch in msg_obj.server.channels:
                if ch.name == 'bot':
                    self.channel = ch
                    break
        else:
            self.channel = msg_obj.channel
        if msg[1] == 'list':
            playlists = [x.split('.')[0] for x in listdir('playlists/')]
            await self.bot.send_message(msg_obj.channel, 'Available playlists: `{}`'.format('|'.join(playlists)))
            return True

        if len(msg) > 2:
            f = open(playlist_name, 'wt')
            f.write('%s\n' % msg[2])
            f.close()

        if not isfile(playlist_name):
            await self.bot.send_message(msg_obj.channel, 'Invalid playlist!')
            return True

        playlist_url = open(playlist_name, 'rt').read().split('\n')[0]
        items = await self.extract_info(url=playlist_url, process=False, download=False)

        for num, item in enumerate(items['entries']):
            if num > 0 and not self.song:
                self.play()

            try:
                x = await self.process_info(item)
                if x is None:
                    continue

                x['requestor'] = msg_obj.author.name
                self.playlist.append(x)
            except:
                continue
        if not self.song:
            self.play()

        return await self.on_queue(msg, msg_obj)


    async def on_play(self, msg, msg_obj):
        if self.voice is None:
            for member in self.bot.get_all_members():
                if member == msg_obj.author and member.voice_channel is not None:
                    self.voice = await self.bot.join_voice_channel(member.voice_channel)

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
            await self.bot.send_message(msg_obj.channel.name, '`Current Volume: %s`' % self.volume)
        else:
            if not str.isdigit(msg[1]): return
            self.volume = int(msg[1]) / 100

            if self.player:
                self.player = self.volume
            await self.bot.send_message(msg_obj.channel, '`{} set the volume to {}`'.format(msg_obj.author, self.volume))

    async def on_skip(self, msg, msg_obj):
        self.skip.add(msg_obj.author)

        level = bot.permissions.get(msg_obj.author.id)

        if (self.player and level in ['mod', 'admin']) or skip.allowed:
            self.player.stop()
            self.player = None

        await self.bot.send_message(msg_obj.channel, '`{} Started a skip request! Need 1 more person to request a skip to continue!`'.format(msg_obj.author))


async def on_message(bot, msg, msg_obj):
    if msg_obj.server not in bot.yt:
        bot.yt[msg_obj.server] = YoutubePlayer(bot, msg_obj.channel)

    return await bot.yt[msg_obj.server].process_commands(msg, msg_obj)
