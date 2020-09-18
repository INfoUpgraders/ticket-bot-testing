import discord
from discord.ext import commands
TOKEN = ''
bot = commands.Bot(command_prefix='!')


@bot.event
async def on_ready():
    print(f'Logged in as: {bot.user}')
    print(f'With ID: {bot.user.id}')



bot.run(TOKEN)
