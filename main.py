import os
import discord
import asyncio
import sqlite3
import logging
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from random import randint

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_user_table():
    connection = sqlite3.connect(f"{BASE_DIR}\\user_warnings.db")
    cursor = connection.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "users_per_guild" (
            "user_id" INTEGER,
            "warning_count" INTEGER,
            "guild_id" INTEGER,
            PRIMARY KEY("user_id","guild_id")
        )      
    """)

    connection.commit()
    connection.close()

create_user_table()

def increase_and_get_warnings(user_id: int, guild_id: int):
    connection = sqlite3.connect(f"{BASE_DIR}\\user_warnings.db")
    cursor = connection.cursor()
    
    cursor.execute("""
        SELECT warning_count
        FROM users_per_guild
        WHERE (user_id = ?) AND (guild_id = ?);
    """, (user_id, guild_id))
    
    result = cursor.fetchone()
    
    if result == None:
        cursor.execute("""
            INSERT INTO users_per_guild (user_id, warning_count, guild_id)
            VALUES (?, 1, ?);
        """, (user_id, guild_id))
        
        connection.commit()
        connection.close()
        
        return 1
    
    cursor.execute("""
        UPDATE users_per_guild
        SET warning_count = ?
        WHERE (user_id = ?) AND (guild_id = ?);
    """, (result[0] + 1, user_id, guild_id))
    
    connection.commit()
    connection.close()
    
    return result[0] + 1

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler('discord.log', encoding = 'utf-8', mode = 'w')
intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix = '!', intents = intents)

def is_moderator_or_owner():
    async def predicate(interaction):
        if interaction.user.id == interaction.guild.owner.id:
            return True
        
        if any(role.name == 'Moderator' for role in interaction.user.roles):
            return True
        
        raise app_commands.CheckFailure("You need to be a Moderator or the server owner to use this command.")
    
    return app_commands.check(predicate)

GUILD_ID = discord.Object(id = 1465063962604212306)

EMOJI_ROLE_MAP = {
    '⚔️': 'dps',
    '🛡️': 'tank',
    '❤️‍🩹': 'healer'
}

profanities = [
    'fuck', 'shit', 'asshole', 'bitch', 'dick', 'pussy', 'cunt', 'faggot', 'dyke',
    'cock', 'nigger', 'chink', 'spic', 'gook', 'wetback', 'honky', 'kike',
    'beaner', 'gringo']


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user.name} is now online")

@bot.event
async def on_member_join(member):
    await member.send(f"Welcome to the server, {member.name}")

@bot.event
async def on_message(message):
    if message.author.id != bot.user.id:
        if any(profanity.lower() in message.content.lower() for profanity in profanities):
            num_warnings = increase_and_get_warnings(message.author.id, message.guild.id)
            
            if num_warnings >= 3:
                await message.author.ban(reason = "Exceeded 3 strikes for profanity usage")
                await message.channel.send(f"{message.author.mention} has been banned for repeated profanity")
            else:
                await message.channel.send(f"{message.author.mention} This is Warning #{num_warnings}. If you reach 3 warnings, you will be banned.")
                await message.delete()
            
    else:
        return
    
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, member):
    if member.id != bot.user.id:
        if hasattr(bot, 'roles_message_id') and reaction.message.id == bot.roles_message_id:
            emoji = str(reaction.emoji)
            
            if emoji in EMOJI_ROLE_MAP:
                role_name = EMOJI_ROLE_MAP[emoji]
                role = discord.utils.get(member.guild.roles, name = role_name)
                
                if role:
                    await member.add_roles(role)
        elif hasattr(bot, 'ticket_message_id') and reaction.message.id == bot.ticket_message_id:
            if str(reaction.emoji) == '✉️':
                guild = member.guild
                
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                
                mod_role = discord.utils.get(guild.roles, name='Moderator')
                
                if mod_role:
                    overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
                channel = await guild.create_text_channel(f'ticket-{member.name}', overwrites=overwrites, category=None)
                
                await channel.send(f"{member.mention} Welcome to your support ticket! A moderator will assist you soon.")
                await reaction.remove(member)
        else:
            return
    else:
        return

@bot.event
async def on_reaction_remove(reaction, member):
    if member.id != bot.user.id:
        if hasattr(bot, 'roles_message_id') and reaction.message.id == bot.roles_message_id:
            emoji = str(reaction.emoji)
            
            if emoji in EMOJI_ROLE_MAP:
                role_name = EMOJI_ROLE_MAP[emoji]
                role = discord.utils.get(member.guild.roles, name = role_name)
                
                if role:
                    await member.remove_roles(role)
        else:
            return
    else:
        return

@bot.tree.command(name = 'help', description = "Helpful information about the bot")
async def help(interaction: discord.Interaction):
    overview = (
        "Welcome to Hero_bot!\n"
        "Created by: Bl4ckH4wkTTV\n\n"
        "This bot serves as a general multi-purpose tool for server management and most basic tasks\n\n"
        "Below is a list of commands broken down into two categories: public use and moderator-only"
    )
    
    public_commands = (
        "/help\n"
        "/server\n"
        "/hello\n"
        "/goodbye\n"
        "/roll\n"
        "/shake"
    )
    
    moderator_commands = (
        "/ticket\n"
        "/close\n"
        "/roles\n"
        "/assign\n"
        "/remove\n"
        "/poll\n"
        "/purge"
    )
    
    embed = discord.Embed(title = 'Bot Support', description = overview, color = discord.Color.red())
    embed.set_thumbnail(url = bot.user.avatar.url)
    embed.add_field(name = 'Public Commands', value = public_commands, inline = False)
    embed.add_field(name = 'Moderator Commands', value = moderator_commands, inline = False)
    
    await interaction.response.send_message(embed = embed)

@bot.tree.command(name = 'server', description = "A brief server overview")
async def server(interaction: discord.Interaction):
    guild = interaction.guild
    
    description = (
        f"Guild Created on {guild.created_at.strftime('%B %d, %Y')}\n\n"
        f"Member Count: {guild.member_count}\n"
        f"Owner: {guild.owner.mention}\n"
        f"Text Channels: {len(guild.text_channels)}\n"
        f"Voice Channels: {len(guild.voice_channels)}\n"
        f"Roles: {len(guild.roles)}\n"
        f"Verification Level: {guild.verification_level}\n"
        f"Features: {', '.join(guild.features) if guild.features else 'None'}"
    )
    
    embed = discord.Embed(title = f"{guild.name} Server Information", description = description, color = discord.Color.red())
    embed.set_thumbnail(url = guild.icon.url if guild.icon else None)
    
    await interaction.response.send_message(embed = embed)

@bot.tree.command(name = 'purge', description = "Purge messages from current chat channel")
@is_moderator_or_owner()
async def purge(interaction: discord.Interaction, amount: int):
    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message("This command can only be used in text channels")
        return
    
    if amount < 1 or amount > 100:
        await interaction.response.send_message("Specify a number between 1 and 100")
        return
    
    await interaction.response.send_message("Purging Messages...", ephemeral = True)
    
    deleted = await interaction.channel.purge(limit = amount)
    
    await interaction.followup.send(f"Successfully purged {len(deleted)} messages", ephemeral = True)

@bot.tree.command(name = 'ticket', description = "Create a support ticket generator")
@is_moderator_or_owner()
async def ticket(interaction: discord.Interaction):    
    embed = discord.Embed(title = "Support Ticket", description = "React with ✉️ to open a support ticket", color = discord.Color.blue())
    embed.set_thumbnail(url = 'https://img.icons8.com/?size=100&id=3665&format=png&color=000000')
    
    await interaction.response.send_message(embed = embed)
    
    ticket_message = await interaction.original_response()
    
    await ticket_message.add_reaction('✉️')
    
    bot.ticket_message_id = ticket_message.id

@bot.tree.command(name = 'close', description = "Close the current support ticket")
@is_moderator_or_owner()
async def close(interaction: discord.Interaction):
    if interaction.channel.name.startswith('ticket-'):
        await interaction.response.send_message("Ticket resolved. Closing channel...")
        await asyncio.sleep(2)
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("This command can only be used in a ticket channel.")
        
@bot.tree.command(name = 'assign', description = "Assign role to a member")
@is_moderator_or_owner()
async def assign(interaction: discord.Interaction, member: discord.Member, *, role_name: str):
    role = discord.utils.get(member.guild.roles, name = role_name)
    
    if role:
        await member.add_roles(role)
        await interaction.response.send_message(f"{member.mention} has been assigned to {role_name}")
    else:
        await interaction.response.send_message("Role does not exist")

@bot.tree.command(name = 'remove', description = "Unassign role from a member")
@is_moderator_or_owner()
async def remove(interaction: discord.Interaction, member: discord.Member, *, role_name: str):
    role = discord.utils.get(member.guild.roles, name = role_name)
    
    if role:
        await member.remove_roles(role)
        await interaction.response.send_message(f"{member.mention} has been unassigned from {role_name}")
    else:
        await interaction.response.send_message("Role does not exist")

@bot.tree.command(name = 'roles', description = "React to set roles")
@is_moderator_or_owner()
async def roles(interaction: discord.Interaction):
    description = (
        "React to this message to set your roles!\n\n"
        "⚔️ dps \n"
        "🛡️ tank \n"
        "❤️‍🩹 healer"
    )
    
    embed = discord.Embed(title = "Set your roles", description = description, color = discord.Color.red())
    embed.set_thumbnail(url = 'https://img.icons8.com/?size=100&id=VbHk5FdAyj8k&format=png&color=000000')
    
    await interaction.response.send_message(embed = embed)
    
    roles_message = await interaction.original_response()
    
    emojis = ['⚔️', '🛡️', '❤️‍🩹']
    
    for emoji in emojis:
        await roles_message.add_reaction(emoji)
    
    bot.roles_message_id = roles_message.id

@bot.tree.command(name = 'poll', description = "Create a poll")
@is_moderator_or_owner()
async def poll(interaction: discord.Interaction, *, question: str):
    embed = discord.Embed(title = 'New Poll', description = question)
    embed.set_thumbnail(url = 'https://img.icons8.com/?size=100&id=119580&format=png&color=000000')
    
    await interaction.response.send_message(embed = embed)
    
    poll_message = await interaction.original_response()
    
    await poll_message.add_reaction('👍🏻')
    await poll_message.add_reaction('👎🏻')

@bot.tree.command(name = 'hello', description = "Greet the user")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello there {interaction.user.mention}")

@bot.tree.command(name = 'goodbye', description = "Say goodbye to the user")
async def goodbye(interaction: discord.Interaction):
    await interaction.response.send_message(f"See you next time {interaction.user.mention}")

@bot.tree.command(name = 'roll', description = "Roll a random number")
async def roll(interaction: discord.Interaction, lower_limit: int, upper_limit: int):
    if lower_limit >= upper_limit:
        await interaction.response.send_message(f"{interaction.user.mention} Lower limit must be less than upper limit.")
        return
    
    await interaction.response.send_message(f"Roll({lower_limit} to {upper_limit}): {randint(lower_limit, upper_limit)}")

@bot.tree.command(name = 'shake', description = "Shake the magic 8-ball")
async def shake(interaction: discord.Interaction, *, question: str):
    responses = [
        "It is certain.",
        "It is decidedly so.",
        "Without a doubt.",
        "Yes definitely.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful."
    ]
    
    if not question.strip():
        await interaction.response.send_message("You need to ask a question!")
    else:
        response = responses[randint(0, len(responses) - 1)]
        embed = discord.Embed(title = 'Magic 8-Ball', description = f"**Question:** {question}\n**Answer:** {response}")
        embed.set_thumbnail(url = 'https://img.icons8.com/?size=100&id=PSYB5B3EHx6s&format=png&color=000000')
        
        await interaction.response.send_message(embed=embed)

bot.run(TOKEN, log_handler = handler, log_level = logging.DEBUG)