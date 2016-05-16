def on_load(bot):
    bot.permissions = {}
    for line in open('permissions.txt', 'rt').read().split('\n')[:-1]:
        args = line.split(':')
        bot.permissions[args[0]] = args[1]

async def on_message(bot, msg, msg_obj):
    if msg[0] in ['role', 'permission']:
        level = bot.permissions.get(msg_obj.author.id)

        if level is None or level not in ['user', 'mod', 'admin']:
            return

        if msg[1] == 'list':
            s = ''
            for user, permission in bot.permissions.items():
                for m in bot.get_all_members():
                    if m.id == user:
                        s += '**%s**: `%s`\n' % (m.name, permission)
                        break
            await bot.send_message(msg_obj.channel, s)
            return True
        if msg[1] == 'add' and level == 'admin':
            status = msg[2]
            user = ' '.join(msg[3:])

            for u in bot.get_all_members():
                if user.lower() == u.name.lower():
                    bot.permissions[u.id] = status
                    break
            f = open('permissions.txt', 'wt')
            for k,v in bot.permissions.items():
                f.write('%s:%s\n' % (k, v))
            f.close()
            return True
