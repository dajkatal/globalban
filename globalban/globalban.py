from redbot.core import commands, Config
import discord
from discord.ext.commands import UserConverter, has_permissions
import asyncio
from datetime import date, datetime, timedelta
import time


class BanSync(commands.Cog):
    """
    A cog that allows for global bans and unbans.

    Commands :
        [p]globalban <name> or <name#discrim> or <mention> or <id>: Bans a user from all connected servers.
        [p]globalunban <id>: Unbans a user from all connected servers.
        [p]globalbans: Gives all the people who are banned.
        [p]bansync: Syncs all global bans across all servers.
        [p]syncedservers: Shows all the synced servers.
        [p]sync: Adds a server to the synced list if it is not already there and re-syncs all the global bans.
        [p]delsync: Removes a server from the synced server list.
    """

    def __init__(self, bot):
        """
        Initializes all the required variables and runs the
        initiate function to run all the asynchronous code.

        Input: BOT
        Output: A bot with information on all the players that are banned globally.
        """
        commands.Cog.__init__(self)
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1001)
        self.initiate = self.bot.loop.create_task(self.initiate())
        self.to_time = 0
        self.scheduled = 'weekly'
        self.task = self.bot.loop.create_task(self.bansync_scheduled())
        self.tempbans = self.bot.loop.create_task(self.checktempbans())

    async def initiate(self):
        """
        Checks if the bot's config has a list of global bans,
        and if not, it creates a blank dictionary for them to be stored.

        Input: Nothing
        Output: Nothing OR a config with a blank template for global bans to be stored inside.
        """
        await self.bot.wait_until_ready()
        if await self.config.global_bans() is None:
            global_bans = {
                'global_bans': {
                }
            }
            self.config.register_global(**global_bans)
        if await self.config.synced_servers() is None:
            synced_servers = {
                'synced_servers': [i.id for i in self.bot.guilds]
            }
            self.config.register_global(**synced_servers)
        if await self.config.scheduled() is None:
            scheduled = {
                'scheduled': ['weekly']
            }
            self.config.register_global(**scheduled)
        else:
            self.scheduled = await self.config.scheduled()
            self.scheduled = self.scheduled[0]

    async def bansync_scheduled(self):
        """
        An looped task the runs once every

        Input: Nothing
        Output: A server sync for all the global bans once a week.
        """
        while True:
            await self.bansync_root()
            time = datetime.now()
            month, day, day_num, hour, minutes, seconds = int(time.strftime('%m')), time.strftime('%a'), int(time.strftime('%d')), int(time.strftime('%H')), int(time.strftime('%M')), int(time.strftime('%S'))
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            month_length = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

            if self.scheduled == 'daily':
                self.to_time = ((60 - minutes) * 60) + (60 - seconds)
                self.to_time += (24 - hour - 1) * 60 * 60
                await self.bot.get_channel(self.sync_send_message).send('Done. The bans will now sync {}. Time to sleep: {}'.format(self.scheduled, self.to_time))
                await asyncio.sleep(self.to_time)
            elif self.scheduled == 'weekly':
                self.to_time = ((60 - minutes) * 60) + (60 - seconds)
                self.to_time += (24 - hour - 1) * 60 * 60
                self.to_time += (7-(days.index(day) + 1)) * 24 * 60 * 60
                await self.bot.get_channel(self.sync_send_message).send('Done. The bans will now sync {}. Time to sleep: {}'.format(self.scheduled, self.to_time))
                await asyncio.sleep(self.to_time)
            elif self.scheduled == 'monthly':
                self.to_time = ((60-minutes) * 60) + (60-seconds)
                self.to_time += (24 - hour - 1) * 60 * 60
                self.to_time += (month_length[int(month)-1] - day_num) * 24 * 60 * 60
                await self.bot.get_channel(self.sync_send_message).send('Done. The bans will now sync {}. Time to sleep: {}'.format(self.scheduled, self.to_time))
                await asyncio.sleep(self.to_time)

    @has_permissions(ban_members=True)
    @commands.command()
    async def synctime(self, ctx, *, schedule_at):
        """
        Changes the time when the bot automatically syncs all the bans.

        Input: Scheduled Time
        Output: Nothing

        Usage: [p]synctime <'Daily' Or 'Weekly' Or 'Monthly'>
        """
        try:
            schedule_at = schedule_at.lower()
            if schedule_at in ('daily', 'weekly', 'monthly'):
                async with self.config.scheduled() as scheduled:
                    scheduled[0] = schedule_at
                    self.scheduled = schedule_at
                    self.task.cancel()
                    self.sync_send_message = ctx.channel.id
                    self.task = self.bot.loop.create_task(self.bansync_scheduled())
            else:
                await ctx.send('Oops, please use daily, weekly or monthly.')
        except AttributeError:
            await ctx.send('Oops, please use daily, weekly or monthly.')
        except Exception as ex:
            await ctx.send('Something went wrong, but im not sure what. Please check how to use the command.')

    async def report_failure(self, failed_servers):
        """
        This function is called whenever the bot does not have sufficient permissions on certain servers.
        """
        AppInfo = await self.bot.application_info()
        Owner = AppInfo.owner
        message = "I have not been setup correctly. ( Check if i'm admin or if I can ban/unban other players. ) \nThe BanSync failed on these servers: \n"
        for number, failure in enumerate(failed_servers):
            message += '\n{}. {}'.format(number + 1, failure)
        await Owner.send(message)
        return True

    async def bansync_root(self):
        """
        Checks through ever connected server and checks if every user in
        global ban dictionary is banned. If not, it re-bans them.

        Input: Nothing
        Output: A server sync for all the global bans.
        """
        async with self.config.global_bans() as global_bans:
            failed_servers = []
            async with self.config.synced_servers() as servers:
                for server in servers:
                    try:
                        server = self.bot.get_guild(server)
                        if server is None:
                            del servers[servers.index(server)]
                            continue
                        bans = [b.user.id for b in await server.bans()]
                        for id, name in global_bans.items():
                            id = int(id)
                            if id not in bans:
                                await self.bot.get_guild(server.id).ban(discord.Object(id=id), delete_message_days=0)
                    except discord.errors.Forbidden:
                        failed_servers.append(server.name)

            if len(failed_servers) > 0:
                await self.report_failure(failed_servers)

    @has_permissions(ban_members=True)
    @commands.command()
    async def bansync(self, ctx):
        """
        Syncs all global bans across all servers.

        Input: CTX
        Output: bansync_root
        """
        await self.bansync_root()
        await ctx.send('Done. If there is any error, the owner has been notified.')

    async def checktempbans(self):
        async with self.config.global_bans() as banned_users:
            async with self.config.synced_servers() as servers:
                while True:
                    for id, member in banned_users.items():
                        if member[2] < time.mktime(datetime.now().timetuple()):
                            for server in servers:
                                server = self.bot.get_guild(server)
                                if server is None:
                                    del servers[servers.index(server)]
                                    continue
                                try:
                                    print(banned_users)
                                    await server.unban(discord.Object(id=int(id)))
                                    del (banned_users[id])
                                    print('{} has been unbanned.'.format(member[0]))
                                except:
                                    pass
                    await asyncio.sleep(60)




    @commands.command()
    async def globalbans(self, ctx):
        """
        Shows all the global bans.

        Input: CTX
        Output: Shows everyone who is banned throughout all servers
        """
        message = 'Here are the globally banned users:\n'
        async with self.config.global_bans() as banned_users:
            for number, user in enumerate(banned_users.values()):
                message += '\n{}. {} - Reason: {} - Time: {}'.format(number + 1, user[0], user[1], user[3])
            if len(banned_users.keys()) == 0:
                message += '\nNone'
            await ctx.send(message)

    @has_permissions(ban_members=True)
    @commands.command()
    async def globalban(self, ctx, member: discord.Member, reason, time_of_ban):
        """"
        Bans a user from all connected servers.
        
        If you dont want to add a reason or time_of_ban, simple use /. This will give not reason and/pr ban the user forever.
        Usage: [p]globalban <name> or <name#discrim> or <mention> or <id> <reason> <time of ban>
        """
        try:
            if reason is '/':
                reason = 'Not Given'
            rawbantime = time_of_ban
            if rawbantime is not '/':
                keycodes = {'Y': 365, 'M': 30, 'W': 7, 'D': 1, 'H': 1, 'M': 1, 'S': 1}

                total = {'D': 0, 'H': 0, 'M': 0, 'S': 0}

                process_errors = []

                processed_string = rawbantime.split('-')

                for i in processed_string:
                    number = int(''.join(list(filter(lambda x: x.isdigit(), i))))
                    keycode = (''.join(list(filter(lambda x: x.isalpha(), i)))).upper()

                    try:
                        number = number * keycodes[keycode]
                        if keycode in ['Y', 'MM', 'W']:
                            keycode = 'D'
                        total[keycode] += number
                    except KeyError:
                        process_errors.append(keycode)
                    except:
                        ctx.send('Something went wrong, but im not sure what. Please check how to use the command.')

                if len(process_errors) is not 0:
                    error_string = ''
                    for error in process_errors:
                        if process_errors[-1] is error and len(process_errors) is not 1:
                            error_string += ' and ' + error
                        else:
                            if len(error_string) is 0:
                                error_string += error
                            else:
                                error_string += ', ' + error

                    print("I don't have these keycode(s): {}. Please check how to use the command.".format(error_string))
                    return True

                bantime_string = ''

                for timestamp, value in total.items():
                    if value is not 0:
                        last_value = timestamp

                for rawtimestamp, amount in total.items():
                    if rawtimestamp is 'D':
                        timestamp = 'days' if amount > 1 else 'day'
                    if rawtimestamp is 'H':
                        timestamp = 'hours' if amount > 1 else 'hour'
                    if rawtimestamp is 'M':
                        timestamp = 'minutes' if amount > 1 else 'minute'
                    if rawtimestamp is 'S':
                        timestamp = 'seconds' if amount > 1 else 'second'
                    if amount > 0:
                        if len(bantime_string) is 0:
                            bantime_string += '{} {}'.format(amount, timestamp)
                        elif rawtimestamp == last_value:
                            bantime_string += ' and {} {}'.format(amount, timestamp)
                        else:
                            bantime_string += ', {} {}'.format(amount, timestamp)

                bantime = time.mktime(datetime.now().timetuple()) + timedelta(days=total['D'], hours=total['H'], minutes=total['M'], seconds=total['S']).total_seconds()
            else:
                bantime = timedelta(days=100).total_seconds() * 1000000
                bantime_string = 'Forever'

            if member is not 0:
                async with self.config.synced_servers() as servers:
                    failed_servers = []
                    successful = 0
                    for server in servers:
                        server = self.bot.get_guild(server)
                        if server is None:
                            del servers[servers.index(server)]
                            continue
                        try:
                            bans = [b.user for b in await server.bans()]
                            if member not in bans:
                                await member.send('You have been banned from all {} servers for {} because of the reason: {}.'.format('Gaming For Life', bantime_string, reason))
                                await server.ban(member, delete_message_days=0)
                                successful += 1
                                print('before')
                                print('after')
                            else:
                                pass
                        except discord.errors.Forbidden:
                            failed_servers.append(server.name)
                    async with self.config.global_bans() as global_bans:
                        if len(failed_servers) is 0:
                            global_bans.update({member.id: [member.name, reason, bantime, bantime_string]})
                    if successful is len(servers):
                        await ctx.send('%s has been banned from all connected servers.' % member.name)
                    elif successful > 0 and successful < len(servers):
                        await ctx.send('%s has been banned from some of the connected servers.' % member.name)
                    else:
                        await ctx.send('We have not been able to ban %s from the connected servers.' % member.name)

                    if len(failed_servers) > 0:
                        await self.report_failure(failed_servers)
            if member is None:
                await ctx.send('It seems like %s is not connected to any of the servers I manage. :(' % member.name)

            if member is 0:
                await ctx.send('Please enter a username. \nThis command is used like this: --globalban <username>.')
        except discord.errors.Forbidden:
            await ctx.send('Looks like you cannot do that.')
        #except:
        #    await ctx.send('Something went wrong, but im not sure what. Please check how to use the command.')

    @has_permissions(ban_members=True)
    @commands.command()
    async def globalunban(self, ctx, *, id):
        """
        Unbans a user from all connected servers.

        Usage: [p]globalunban <id>
        """
        try:
            failed_servers = []
            successful = 0
            async with self.config.global_bans() as banned_users:
                if id in list(banned_users.keys()):
                    async with self.config.synced_servers() as servers:
                        for server in servers:
                            server = self.bot.get_guild(server)
                            if server is None:
                                del servers[servers.index(server)]
                                continue
                            try:
                                await server.unban(discord.Object(id=int(id)))
                                successful += 1
                            except discord.errors.Forbidden:
                                failed_servers.append(server.name)
                        if successful is len(servers):
                            await ctx.send('%s has been unbanned from all connected servers.' % banned_users[id][0])
                        elif successful > 0 and successful < servers:
                            await ctx.send('%s has been unbanned from some of the connected servers.' % banned_users[id][0])
                        else:
                            await ctx.send('We have not been able to unban %s from the connected servers.' % banned_users[id][0])
                        if len(failed_servers) is 0:
                            del(banned_users[id])
                            return True
                if len(failed_servers) > 0:
                    await self.report_failure(failed_servers)
                if banned_users[id] is None:
                    # This will call the KeyError exception to tell the user that the ID is wrong.
                    pass
                if type(id) is not int:
                    await ctx.send("This command requires the user's id")
                if id is 0:
                    await ctx.send('Please enter an ID. \nThis command is used like this: --globalunban <ID>.')
        except KeyError:
            await ctx.send('This user may not actually be banned or the ID is wrong')
        except:
            await ctx.send('Something went wrong, but im not sure what. Please check how to use the command.')

    @has_permissions(ban_members=True)
    @commands.command()
    async def syncedservers(self, ctx):
        """
        Shows all the synced servers.

        Input: CTX
        Output: A message of all the synced servers.
        """
        async with self.config.synced_servers() as servers:
            message = "The current synced servers:\n"
            for number, server in enumerate(servers):
                server = self.bot.get_guild(server)
                if server is None:
                    del servers[servers.index(server)]
                    continue
                message += '\n{}. {}'.format(number + 1, server.name)
        await ctx.send(message)

    @has_permissions(ban_members=True)
    @commands.command()
    async def sync(self, ctx, *, id):
        """
        Adds a server to the synced list if it is not already there.
        Then it re-syncs the global bans.

        Input: CTX and ID
        Output: Nothing

        Usage: [p]sync <ID>
        """
        try:
            id = int(id)
            server = self.bot.get_guild(id)
            async with self.config.synced_servers() as servers:
                if server is not None:
                    if server not in servers:
                        servers.append(server.id)
                        await ctx.send('The server, {}, has been added to the synced server list. Give me a moment while I sync all the global bans to its server.'.format(server.name))
                        await self.bansync_root()
                    else:
                        await ctx.send('This server is already in the synced list.')
                else:
                    await ctx.send('This server does not exist or I am not connected to it. Please enter a valid server ID.')
        except ValueError:
            await ctx.send('The ID must be a number.')
        except:
            await ctx.send('Something went wrong, but im not sure what.')

    @has_permissions(ban_members=True)
    @commands.command()
    async def delsync(self, ctx, *, id):
        """
        Removes a server from the synced server list.

        Input: CTX and ID
        Output: Nothing

        Usage: [p]delsync <ID>
        """
        try:
            id = int(id)
            server = self.bot.get_guild(id)
            if server is not None:
                async with self.config.synced_servers() as servers:
                    synced_server_ids = [i for i in servers]
                    if id in synced_server_ids:
                        del servers[synced_server_ids.index(id)]
                        await ctx.send('The server, {}, has been removed from the synced server list.'.format(server.name))
                    else:
                        await ctx.send('This server is not in the synced list.')
            else:
                await ctx.send('This server does not exist or I am not connected to it. Please enter a valid server ID.')
        except ValueError:
            await ctx.send('The ID must be a number.')
        except:
            await ctx.send('Something went wrong, but im not sure what.')
