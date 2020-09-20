import discord
import json
from discord.ext import commands, tasks
import asyncio

import os.path
from discord.utils import get
TOKEN = ''
bot = commands.Bot(command_prefix='!')


@bot.event
async def on_ready():
    if os.path.isfile("tickets.json"):
        pass
    else:
        with open("tickets.json", "w") as f:
            json.dump({}, f, indent=4)
    if os.path.isfile("bans.json"):
        pass
    else:
        with open("bans.json", "w") as f:
            json.dump({}, f, indent=4)
    jsonupdate.start()
    print(f'Logged in as: {bot.user}')

@tasks.loop(seconds=5)
async def jsonupdate():
    with open("tickets.json", "r") as f:
        data = json.load(f)
    with open("bans.json", "r") as f:
        bans = json.load(f)
    for guild in bot.guilds:
        if str(guild.id) in data:
            pass
        else:
            data[str(guild.id)] = {
                "tickets": {},
                "ticketcategories": [],
                "allowedroles": [],
                "transcript": None,
            }
        if str(guild.id) in bans:
            pass
        else:
            bans[str(guild.id)] = {"ids": []}
    with open("tickets.json", "w") as f:
        json.dump(data, f, indent=4)
    with open("bans.json", "w") as f:
        json.dump(bans, f, indent=4)

@bot.command(aliases=["ticket"])
@commands.cooldown(1, 30, commands.BucketType.user)
async def new(ctx):
    """Creates a ticket"""
    guild = ctx.guild
    with open("tickets.json", "r") as f:
        data = json.load(f)

    with open("bans.json", "r") as f:
        bans = json.load(f)
    if ctx.message.author.id in bans[str(guild.id)]["ids"]:
        return await ctx.send("You are ticket banned! Please contact an administrator to get this revoked.")
    category = None
    for channel in guild.channels:
        if channel.type == discord.ChannelType.category:
            if str(channel.name).lower().startswith("tickets-"):
                category = channel
            if str(channel.name).lower().startswith("tickets-1") and len(channel.channels) < 49:
                category = channel
                break

    if category is None:
        category = await guild.create_category("tickets-1")
    if len(category.channels) >= 49:
        category = await guild.create_category(f"tickets-{int(str(category.name).split('-')[1]) + 1}")
    ticketdata = data[str(ctx.guild.id)]
    ticketchannel = await category.create_text_channel(f"ticket-{ctx.author.name}")
    await ticketchannel.set_permissions(guild.default_role, read_messages=False, send_messages=False)
    await ticketchannel.set_permissions(ctx.author, read_messages=True, send_messages=True)
    for allowedrole in ticketdata["allowedroles"]:
        role = get(guild.roles, id=allowedrole)
        await ticketchannel.set_permissions(role, read_messages=True, send_messages=True)
    embed = discord.Embed(title="Ticket created", description=f"Your ticket can be found at {ticketchannel.mention}.")
    ticketdata["tickets"][str(ticketchannel.id)] = {
        "user": ctx.author.id,
        "claimuser": None,
    }
    data[str(ctx.guild.id)] = ticketdata
    await ctx.send(embed=embed)
    embed = discord.Embed(title="Ticket Channel", description="Please describe your problem, our support team will be with you shortly.")
    rolesandstuff = []
    for allowedrole in ticketdata["allowedroles"]:
        role = get(guild.roles, id=allowedrole)
        rolesandstuff.append(role.mention)
    allsupport = ", ".join(rolesandstuff)
    await ticketchannel.send(f"{ctx.author.mention}, {allsupport}",embed=embed)
    with open("tickets.json", "w") as f:
        json.dump(data, f, indent=4)
@new.error
async def new_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"That command is on cooldown, try again in {round(error.retry_after)} seconds")
    else:
        raise error

@bot.command()
@commands.has_permissions(administrator=True)
async def transcriptchannel(ctx, channel: discord.TextChannel):
    with open("tickets.json", "r") as f:
        data = json.load(f)
    data[str(ctx.guild.id)]["transcript"] = channel.id
    await ctx.send(f"Ticket transcript channel set to {channel.mention}.")
    with open("tickets.json", "w") as f:
        json.dump(data, f, indent=4)

@bot.command()
async def close(ctx):
    """Closes a ticket"""
    guild = ctx.guild
    with open("tickets.json", "r") as f:
        data = json.load(f)
    ticketdata = data[str(guild.id)]
    transcriptc = get(guild.channels, id=ticketdata["transcript"])
    messages = await ctx.message.channel.history(limit=10000).flatten()
    allmessage = []
    messages.reverse()
    for message in messages:
        if message.author == bot.user or message.content == "!close":
            continue
        else:
            x = f"""
From: {message.author}
At: {message.created_at.strftime('%m/%d/%Y, %H:%M:%S')}

{message.clean_content}
            """
            allmessage.append(x)


    hasperms = False
    for allowedrole in ticketdata["allowedroles"]:
        modrole = get(guild.roles, id=allowedrole)
        for role in ctx.author.roles:
            if role == modrole:
                hasperms = True
    if hasperms:
        if str(ctx.message.channel.id) in ticketdata["tickets"]:
            ticketdata["tickets"].pop(str(ctx.message.channel.id))
            with open(f"{ctx.channel.name}_Transcript", "w", encoding="utf-8") as f:
                for message in allmessage:
                    f.write(message)
            with open(f"{ctx.channel.name}_Transcript", "rb") as f:
                await transcriptc.send(f"{ctx.message.channel.name}", file=discord.File(f, f"transcript-{ctx.channel.name}.txt"))
            await ctx.send("Closing ticket.")
            await asyncio.sleep(5)
            await ctx.message.channel.delete()
        else:
            await ctx.send("This is not a ticket channel!")
    else:
        await ctx.send("You cannot close this ticket!")
    data[str(guild.id)] = ticketdata
    with open("tickets.json", "w") as f:
        json.dump(data, f, indent=4)

@bot.command()
@commands.has_any_role("Moderators", "Administrators", "^", "Founder")
async def ticketban(ctx, member : discord.Member):
    with open("bans.json", "r") as f:
        bans = json.load(f)
    if member.id in bans[str(ctx.guild.id)]["ids"]:
        await ctx.send(f"{member.mention} is already ticket banned!")
    else:
        bans[str(ctx.guild.id)]["ids"].append(member.id)
        await ctx.send(f"{member.mention} is now ticket banned.")
    with open("bans.json", "w") as f:
        json.dump(bans, f, indent=4)

@bot.command()
@commands.has_any_role("Moderators", "Administrators", "^", "Founder")
async def revoketicketban(ctx, member : discord.Member):
    with open("bans.json", "r") as f:
        bans = json.load(f)
    if member.id in bans[str(ctx.guild.id)]["ids"]:
        bans[str(ctx.guild.id)]["ids"].remove(member.id)
        await ctx.send(f"{member.mention} is no longer ticket banned.")
    else:
        await ctx.send(f"{member.mention} is not ticket banned!")
    with open("bans.json", "w") as f:
        json.dump(bans, f, indent=4)
bot.run(TOKEN)
