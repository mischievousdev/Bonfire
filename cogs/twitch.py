from discord.ext import commands
from .utils import config
from .utils import checks
import urllib.request
import urllib.parse
import asyncio
import discord
import json
import re


def channelOnline(channel: str):
    url = "https://api.twitch.tv/kraken/streams/{}".format(channel)
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode('utf-8'))
    return data['stream'] is not None


class Twitch:
    """Class for some twitch integration
    You can add or remove your twitch stream for your user
    I will then notify the server when you have gone live or offline"""

    def __init__(self, bot):
        self.bot = bot

    async def checkChannels(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed:
            cursor = config.getCursor()
            cursor.execute('use {}'.format(config.db_default))
            cursor.execute('select * from twitch')
            result = cursor.fetchall()
            for r in result:
                server = discord.utils.find(lambda s: s.id == r['server_id'], self.bot.servers)
                member = discord.utils.find(lambda m: m.id == r['user_id'], server.members)
                url = r['twitch_url']
                live = r['live']
                notify = r['notifications_on']
                user = re.search("(?<=twitch.tv/)(.*)", url).group(1)
                if not live and notify and channelOnline(user):
                    cursor.execute('update twitch set live=1 where user_id="{}"'.format(r['user_id']))
                    await self.bot.send_message(server, "{} has just gone live! "
                                                        "View their stream at {}".format(member.name, url))
                elif live and not channelOnline(user):
                    cursor.execute('update twitch set live=0 where user_id="{}"'.format(r['user_id']))
                    await self.bot.send_message(server,
                                                "{} has just gone offline! Catch them next time they stream at {}"
                                                .format(member.name, url))
            config.closeConnection()
            await asyncio.sleep(30)

    @commands.group(no_pm=True, invoke_without_command=True)
    @checks.customPermsOrRole("none")
    async def twitch(self, *, member: discord.Member=None):
        """Use this command to check the twitch info of a user"""
        if member is not None:
            cursor = config.getCursor()
            cursor.execute('use {}'.format(config.db_default))
            cursor.execute('select twitch_url from twitch where user_id="{}"'.format(member.id))
            result = cursor.fetchone()
            if result is not None:
                url = result['twitch_url']
                user = re.search("(?<=twitch.tv/)(.*)", url).group(1)
                result = urllib.request.urlopen("https://api.twitch.tv/kraken/channels/{}".format(user))
                data = json.loads(result.read().decode('utf-8'))
                fmt = "Username: {}".format(data['display_name'])
                fmt += "\nStatus: {}".format(data['status'])
                fmt += "\nFollowers: {}".format(data['followers'])
                fmt += "\nURL: {}".format(url)
                await self.bot.say("```{}```".format(fmt))
                config.closeConnection()
            else:
                await self.bot.say("{} has not saved their twitch URL yet!".format(member.name))
                config.closeConnection()

    @twitch.command(name='add', pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
    async def add_twitch_url(self, ctx, url: str):
        """Saves your user's twitch URL"""
        try:
            url = re.search("((?<=://)?twitch.tv/)+(.*)", url).group(0)
        except AttributeError:
            url = "https://www.twitch.tv/{}".format(url)
        else:
            url = "https://www.{}".format(url)

        try:
            urllib.request.urlopen(url)
        except urllib.request.HTTPError:
            await self.bot.say("That twitch user does not exist! "
                               "What would be the point of adding a nonexistant twitch user? Silly")
            return

        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select twitch_url from twitch where user_id="{}"'.format(ctx.message.author.id))
        result = cursor.fetchone()
        if result is not None:
            cursor.execute('update twitch set twitch_url="{}" where user_id="{}"'.format(url, ctx.message.author.id))
        else:
            cursor.execute('insert into twitch (user_id,server_id,twitch_url'
                           ',notifications_on,live) values ("{}","{}","{}",1,0)'
                           .format(ctx.message.author.id, ctx.message.server.id, url))
        await self.bot.say("I have just saved your twitch url {}".format(ctx.message.author.mention))
        config.closeConnection()

    @twitch.command(name='remove', aliases=['delete'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
    async def remove_twitch_url(self, ctx):
        """Removes your twitch URL"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select twitch_url from twitch where user_id="{}"'.format(ctx.message.author.id))
        result = cursor.fetchone()
        if result is not None:
            cursor.execute('delete from twitch where user_id="{}"'.format(ctx.message.author.id))
            await self.bot.say("I am no longer saving your twitch URL {}".format(ctx.message.author.mention))
            config.closeConnection()
        else:
            await self.bot.say(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))
            config.closeConnection()

    @twitch.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.customPermsOrRole("none")
    async def notify(self, ctx):
        """This can be used to turn notifications on or off"""
        pass

    @notify.command(name='on', aliases=['start,yes'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
    async def notify_on(self, ctx):
        """Turns twitch notifications on"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select notifications_on from twitch where user_id="{}"'.format(ctx.message.author.id))
        result = cursor.fetchone()
        if result is None:
            await self.bot.say(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))
            config.closeConnection()
            return
        elif result['notifications_on']:
            await self.bot.say("What do you want me to do, send two notifications? Not gonna happen {}".format(
                ctx.message.author.mention))
            config.closeConnection()
            return
        else:
            cursor.execute('update twitch set notifications_on=1 where user_id="{}"'.format(ctx.message.author.id))
            await self.bot.say("I will notify if you go live {}, you'll get a bajillion followers I promise c:".format(
                ctx.message.author.mention))
            config.closeConnection()
            return

    @notify.command(name='off', aliases=['stop,no'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
    async def notify_off(self, ctx):
        """Turns twitch notifications off"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select notifications_on from twitch where user_id="{}"'.format(ctx.message.author.id))
        result = cursor.fetchone()
        if result is None:
            await self.bot.say(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))
            config.closeConnection()
            return
        elif not result['notifications_on']:
            await self.bot.say("I am already set to not notify if you go live! Pay attention brah {}".format(
                ctx.message.author.mention))
            config.closeConnection()
            return
        else:
            cursor.execute('update twitch set notifications_on=0 where user_id="{}"'.format(ctx.message.author.id))
            await self.bot.say(
                "I will not notify if you go live anymore {}, "
                "are you going to stream some lewd stuff you don't want people to see?~".format(
                    ctx.message.author.mention))
            config.closeConnection()
            return


def setup(bot):
    t = Twitch(bot)
    config.loop.create_task(t.checkChannels())
    bot.add_cog(Twitch(bot))
