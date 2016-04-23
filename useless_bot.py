from aiohttp import get
from discord import Client, opus, utils, VoiceClient
import asyncio
from os import environ, listdir
from importlib import import_module, reload

opus.load_opus('/usr/lib/x86_64-linux-gnu/libopus.so.0')

class Bot(Client):
    def __init__(self, prefix, token):
        Client.__init__(self)
        self.prefix = prefix
        self.token = token
        self.plugins = []
        self.playlist = set()

        self.load_plugins()

    def load_plugins(self):
        self.plugins = [import_module('plugins.%s' % module.replace('.py', '')) for module in listdir('plugins/') if '.py' in module and '__' not in module]

        for plugin in self.plugins:
            plugin.on_load(self)

        print('Loaded: %s plugins' % len(self.plugins))

    def run_token(self, token):
        self.token = token
        self.headers['authorization'] = 'Bot %s' % self.token
        self._is_logged_in.set()
        self.loop.run_until_complete(client.connect())


    @asyncio.coroutine
    async def on_message(self, message):
        msg = message.content.split(' ')
        cmd_prefix = msg[0][0]
        msg[0] = msg[0][1:]

        if cmd_prefix == self.prefix:
            remove = False
            for plugin in self.plugins:
                val = await plugin.on_message(self, msg, message)

                if val:
                    remove = True

            if msg[0] == 'reload':
                print(self.permissions.items())
                level = self.permissions.get(message.author.id)
                if level not in ['admin', 'mod']:
                    print('%s tried to be a braindead.' % message.author.id)
                    await self.delete_message(message)
                    return

                remove = True
                self.plugins = [reload(plugin) for plugin in self.plugins]
                for plugin in self.plugins:
                    if hasattr(plugin, 'on_unload'):
                        plugin.on_unload(self)

                print('Loaded: %s plugins' % len(self.plugins))

            if remove:
                await self.delete_message(message)


client = Bot('.', '')
voice = None
yt_player = None

'''
@client.event
async def on_message(msg):
    global yt_player
    if msg.content.startswith('!meme'):
        if yt_player is not None:
            yt_player.stop()

        args = msg.content.split(' ')
        url = args[1]
        yt_player = await client.voice.create_ytdl_player(url)
        yt_player.volume = .2
        yt_player.start()
        await client.send_message(msg.channel, 'Playing: {0} for {1.mention}'.format(yt_player.title, msg.author))

    if msg.content.startswith('!hither'):
        if client.is_voice_connected():
            await client.voice.disconnect()
        for member in client.get_all_members():
            if member == msg.author:
                await client.join_voice_channel(member.voice_channel)

    if msg.content.startswith('!follow'):
        args = msg.content.split(' ')
        name = ' '.join(args[1:])

        for member in client.get_all_members():
            if member.name.lower() == name.lower():
                if member.voice_channel is None:
                    continue
                print( member.voice_channel)
                await client.join_voice_channel(member.voice_channel)
                break

    if msg.content.startswith('!volume'):
        if yt_player is not None and yt_player.is_playing():
            yt_player.volume = int(msg.content.split(' ')[1]) / 100
'''
@client.event
async def on_ready():
    print("Bot is running as the user '{user}'".format(user=client.user.name))
    await client.accept_invite('https://discord.gg/0cjYAVTSMltRtWUT')

print("Running")

client.run_token(environ.get("DISCORD_TOKEN"))
