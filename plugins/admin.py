from discord import Colour
from random import choice, seed
from time import sleep
from datetime import datetime

stop = False
def on_load(bot):
    pass

def on_unload(bot):
    pass

async def on_message(bot, msg, msg_obj):
    global gays
    
    if msg[0] == 'spice':
        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['mod', 'admin']:
            return

        out_msg = '`{}`'
        tmp_msg = ''
        for role in msg_obj.server.roles:
            for i in range(0, 5):
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

        async for message in bot.logs_from(msg_obj.channel, limit=int(msg[1])+1):
            await bot.delete_message(message)
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

    if msg[0] == 'rami':
        await bot.send_message(msg_obj.channel, 'Daily Reminder. **RAMI IS SHIT**', tts=True)
        return True
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
