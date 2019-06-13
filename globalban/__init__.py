from .globalban import BanSync


async def setup(bot):
    ban_sync = BanSync(bot)
    bot.add_cog(ban_sync)
