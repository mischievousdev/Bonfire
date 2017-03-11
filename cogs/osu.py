from . import utils

from discord.ext import commands
import discord

from osuapi import OsuApi, AHConnector

# https://github.com/ppy/osu-api/wiki
BASE_URL = 'https://osu.ppy.sh/api/'
MAX_RETRIES = 5


class Osu:
    def __init__(self, bot):
        self.bot = bot
        self.api = OsuApi(utils.osu_key, connector=AHConnector())
        self.bot.loop.create_task(self.get_users())
        self.osu_users = {}

    async def get_user(self, member, username):
        """A function used to get and save user data in cache"""
        user = self.osu_users.get(member.id)
        if user is None:
            user = await self.get_user_from_api(username)
            if user is not None:
                self.osu_users[member.id] = user
            return user
        else:
            if user.username.lower() == username.lower():
                return user
            else:
                user = await self.get_user_from_api(username)
                if user is not None:
                    self.osu_users[member.id] = user
                return user

    async def get_user_from_api(self, username):
        """A simple helper function to parse the list given and handle failures"""
        user = await self.api.get_user(username)
        try:
            return user[0]
        except IndexError:
            return None

    async def get_users(self):
        """A task used to 'cache' all member's and their Osu profile's"""
        data = await utils.get_content('osu')
        if data is None:
            return

        for result in data:
            member = int(data['member_id'])
            user = await self.get_user_from_api(data['osu_username'])
            if user:
                self.osu_users[member] = user

    @commands.group(invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def osu(self, ctx, member: discord.Member=None):
        """Provides basic information about a specific user

        EXAMPLE: !osu @Person
        RESULT: Informationa bout that person's osu account"""
        if member is None:
            member = ctx.message.author

        user = self.osu_users[member.id]
        if user is None:
            await ctx.send("I do not have {}'s Osu user saved!".format(member.display_name))
            return

        e = discord.Embed(title='Osu profile for {}'.format(user.username))
        e.set_thumbnail(url='https://a.ppy.sh/{}'.format(user_id))
        e.add_field(name='Rank', value=user.pp_rank, inline=False)
        e.add_field(name='Level', value=user.level, inline=False)
        e.add_field(name='Performance Points', value=user.pp_raw, inline=False)
        e.add_field(name='Accuracy', value=user.accuracy, inline=False)
        e.add_field(name='SS Ranks', value=user.count_rank_ss, inline=False)
        e.add_field(name='S Ranks', value=user.count_rank_s, inline=False)
        e.add_field(name='A Ranks', value=user.count_rank_a, inline=False)
        e.add_field(name='Country', value=user.country, inline=False)
        e.add_field(name='Country Rank', value=user.pp_country_rank, inline=False)
        e.add_field(name='Playcount', value=user.playcount, inline=False)
        e.add_field(name='Ranked Score', value=user.ranked_score, inline=False)
        e.add_field(name='Total Score', value=user.total_score, inline=False)

    @osu.command(name='add', aliases=['create', 'connect'])
    @utils.custom_perms(send_messages=True)
    async def osu_add(self, ctx, *, username):
        """Links an osu account to your discord account

        EXAMPLE: !osu add username
        RESULT: Links your username to your account, and allows stats to be pulled from it"""
        author = ctx.message.author
        user = await self.get_user(author, username)
        if user is None:
            await ctx.send("I couldn't find an osu user that matches {}".format(username))
            return

        entry = {
            'member_id': str(author.id),
            'osu_username': user.username
        }

        if not await utils.add_content('osu', entry):
            await utils.update_content('osu', entry, str(author.id))

        await ctx.send("I have just saved your Osu user {}".format(author.display_name))


def setup(bot):
    bot.add_cog(Osu(bot))
