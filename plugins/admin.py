from discord import Colour
from random import choice, seed
from time import sleep
from datetime import datetime
import discord.utils

stop = False
def on_load(bot):
    pass

def a2s(bot, func):
    bot.loop.create_task(func)

async def on_message(bot, msg, msg_obj):


    if msg[0] == 'eval':
        if bot.permissions.get(msg_obj.author.id) != 'admin':
            return

        try:
            await bot.send_message(msg_obj.channel, '```{}```'.format(eval(' '.join(msg[1:]), globals(), locals())))
        except Exception as e:
            print('wtf')
            print(e)
            await bot.send_message(msg_obj.channel, '```{}```'.format(e))
        return True
    if msg[0] == 'mute':
        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['mod', 'admin']:
            return

        voice_channel = None

        for channel in msg_obj.server.channels:
            if str(channel.type) == 'voice':
                for user in channel.voice_members:
                    if user.id == msg_obj.author.id:
                        voice_channel = channel
                        break

        for user in voice_channel.voice_members:
            await bot.server_voice_state(user, mute=True)
            sleep(.75)

        return True
    if msg[0] == 'unmute':
        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['mod', 'admin']:
            return

        voice_channel = None

        for channel in msg_obj.server.channels:
            if str(channel.type) == 'voice':
                for user in channel.voice_members:
                    if user.id == msg_obj.author.id:
                        voice_channel = channel
                        break

        for user in voice_channel.voice_members:
            await bot.server_voice_state(user, mute=False)
            sleep(.75)

        return True
    if msg[0] == 'rgb':
        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['mod', 'admin']:
            return

        out_msg = '`{}`'
        tmp_msg = ''
        for role in msg_obj.server.roles:
            if role.name.lower() != msg[1:]: continue
            for i in range(0, 50):
                print(role.name)
                seed(datetime.now())
                color = Colour(int(''.join([choice('0123456789ABCDEF') for x in range(6)]), 16))
                await bot.edit_role(msg_obj.server, role, color=color)
                tmp_msg += 'Role: %s to %s | %i\n' % (role, color, i)
        await bot.send_message(msg_obj.channel, out_msg.format(tmp_msg))

        return True

    if msg[0] == 'clear':
        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['mod', 'admin']:
            return

        await bot.purge_from(msg_obj.channel, limit=int(msg[1]))
        return True
   
    if msg[0] == 'rcolor':

        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['mod', 'admin']:
            return

        role_name = ' '.join(msg[1:])
        role_obj = None

        for role in msg_obj.server.roles:
            if role.name.lower() == role_name.lower():
                role_obj = role
                break

        if not role_obj:
            return

        s = '`'
        for i in range(0, 10):
            seed(datetime.now())
            color = Colour(int(''.join([choice('0123456789ABCDEF') for x in range(6)]), 16))
            await bot.edit_role(msg_obj.server, role_obj, color=color)
            s += '[%s] Color: %s\n' % (i + 1, color)
            sleep(2)
        await bot.send_message(msg_obj.channel, '%s`' % s)
        return True

    if msg[0] == 'rng':
        await bot.send_message(msg_obj.channel, '%s' % (choice(msg[1:])))
        return True

    if msg[0] == 'troll':
        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['mod', 'admin']:
            return

        user = ' '.join(msg[1:])
        user_obj = None

        for u in msg_obj.server.members:
            if u.name.lower() == user.lower():
                user_obj = u

        if not user_obj: return True

        channels = [x for x in msg_obj.server.channels if str(x.type) == 'voice']

        for i in range(0, 10):
            await bot.send_message(msg_obj.channel, '{0.mention}'.format(user_obj))
            await bot.move_member(user_obj, choice(channels))
            sleep(.15)
        return True

    if msg[0] == 'me':
        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['mod', 'admin']:
            return

        role_name = ' '.join(msg[1:])
        for role in msg_obj.server.roles:
            if role.name.lower() == role_name.lower():
                await bot.add_roles(msg_obj.author, role)


    if msg[0] == 'color':
        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['mod', 'admin']:
            return

        color_str = '0x'+ msg[1]
        role_name = ' '.join(msg[2:])
        color = Colour(int(msg[1], 16))

        for role in msg_obj.server.roles:
            if role.name.lower() == role_name.lower():
                await bot.edit_role(msg_obj.server, role, color=color)
        return True
