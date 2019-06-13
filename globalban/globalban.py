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
        self.task = self.bot.loop.create_task(self.bansync_scheduled())

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
            print(synced_servers['synced_servers'])
            self.config.register_global(**synced_servers)
        if await self.config.scheduled() is None:
            scheduled = {
                'scheduled': ['weekly']
            }
            print(scheduled['scheduled'])
            self.config.register_global(**scheduled)

    async def bansync_scheduled(self):
        """
        An looped task the runs once a week at a time that is dependant on when it is started.
        (ex. If the bot starts at 8:00, it will synchronize bans in one week at 8:00)

        Input: Nothing
        Output: A server sync for all the global bans once a week.
        """
        while True:
            await self.bansync_root()
            scheduled = await self.config.scheduled()[0]
            time = datetime.now()
            month, day, day_num, hour, minutes, seconds = int(time.strftime('%m')), time.strftime('%a'), int(time.strftime('%d')), int(time.strftime('%H')), int(time.strftime('%M')), int(time.strftime('%S'))
            days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            month_days = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
            month_length = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

            if scheduled is 'weekly':
                to_time = (24 - hour) * 60 * 60
                print('Time to sleep:', to_time)
                await asyncio.sleep(to_time)
            if scheduled is 'daily':
                to_time = (24 - hour) * 60 * 60
                to_time += (7-(days.index(day) + 1)) * 24 * 60 * 60
                print('Time to sleep:', to_time)
                await asyncio.sleep(to_time)
            if scheduled is 'monthly':
                to_time = (24 - hour) * 60 * 60
                to_time += (month_length[month_days.index(month)] - day_num) * 24 * 60 * 60
                print('Time to sleep:', to_time)
                await asyncio.sleep(to_time)

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
            if schedule_at is 'daily' or 'weekly' or 'monthly':
                async with self.config.scheduled() as scheduled:
                    scheduled[0] = schedule_at
                    self.task.cancel()
                    self.task = self.bot.loop.create_task(self.bansync_scheduled())
                    await ctx.send('Done. The bans will now sync {}.'.format(schedule_at))
            else:
                await ctx.send('Oops, please use daily, weekly or monthly.')
        except AttributeError:
            await ctx.send('Oops, please use daily, weekly or monthly.')
        #except Exception as ex:
        #    print(ex)
        #    await ctx.send('Something went wrong, but im not sure what. Please check how to use the command.')

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
                message += '\n{}. {}'.format(number + 1, user)
            if len(banned_users.keys()) == 0:
                message += '\nNone'
            await ctx.send(message)

    @has_permissions(ban_members=True)
    @commands.command()
    async def globalban(self, ctx, *, member: discord.Member):
        """
        Bans a user from all connected servers.

        Usage: [p]globalban <name> or <name#discrim> or <mention> or <id>
        """
        try:
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
                                await server.ban(member, delete_message_days=0)
                                successful += 1
                            else:
                                pass
                        except discord.errors.Forbidden:
                            failed_servers.append(server.name)
                    async with self.config.global_bans() as global_bans:
                        global_bans.update({member.id: member.name})
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
        except:
            await ctx.send('Something went wrong, but im not sure what. Please check how to use the command.')

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
                            await ctx.send('%s has been unbanned from all connected servers.' % banned_users[id])
                        elif successful > 0 and successful < servers:
                            await ctx.send('%s has been unbanned from some of the connected servers.' % banned_users[id])
                        else:
                            await ctx.send('We have not been able to unban %s from the connected servers.' % banned_users[id])
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
