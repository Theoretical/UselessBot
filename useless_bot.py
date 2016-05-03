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
                level = self.permissions.get(message.author.id)
                if level not in ['admin', 'mod']:
                    print('%s tried to be a braindead.' % message.author.id)
                    await self.delete_message(message)
                    return

                remove = True
                self.plugins = [reload(plugin) for plugin in self.plugins]
                for plugin in self.plugins:
                    if hasattr(plugin, 'on_unload'):
                        await plugin.on_unload(self)

                print('Loaded: %s plugins' % len(self.plugins))

            if remove:
                await self.delete_message(message)


client = Bot('.', '')

@client.event
async def on_ready():
    print("Bot is running as the user '{user}'".format(user=client.user.name))

client.run(environ.get("DISCORD_TOKEN"))
print("Running")
