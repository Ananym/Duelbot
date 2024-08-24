# this is main.py
import discord
from discord import app_commands, Interaction
from discord.ext import commands, tasks
import asyncio
from game import GameState
from database_handler import DatabaseHandler
import logging
import sys
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# In-memory stores
challenges = {}  # {channel_id: {challenger_id: opponent_id}}
ongoing_matches = {}  # {channel_id: GameState}
player_timeouts = {}  # {channel_id: {player_id: asyncio.Task}}

# Database handler
db_handler = DatabaseHandler("state.db")

# Store configured channels
configured_channels = {}  # {guild_id: channel_id}

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

# Now you can use the logger in your code
logger = logging.getLogger("main")


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user.name}")
    load_configured_channels()
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")


def load_configured_channels():
    global configured_channels
    configured_channels = db_handler.get_configured_channels()
    logger.info(f"Loaded configured channels from database: {configured_channels}")


@bot.tree.command(
    name="usechannel", description="Set the channel for the bot to listen to"
)
async def use_channel(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    guild_id = interaction.guild_id
    db_handler.set_configured_channel(guild_id, channel_id)
    configured_channels[guild_id] = channel_id
    logger.info(f"Updated configured channel for guild {guild_id}: {channel_id}")
    logger.info(f"Current configured channels: {configured_channels}")
    await interaction.response.send_message(
        f"Bot will now listen to commands in this channel.", ephemeral=True
    )


def is_configured_channel():

    async def predicate(interaction: discord.Interaction) -> bool:
        guild_id = interaction.guild_id
        channel_id = interaction.channel_id
        configured_channel_id = configured_channels.get(guild_id)

        is_configured = channel_id == configured_channel_id
        logger.debug(
            f"Checking configured channel - Guild ID: {guild_id}, Channel ID: {channel_id}, Configured Channel ID: {configured_channel_id}, Is configured: {is_configured}"
        )

        if not is_configured:
            if configured_channel_id:
                configured_channel = interaction.guild.get_channel(
                    configured_channel_id
                )
                if configured_channel:
                    await interaction.response.send_message(
                        f"This command can only be used in the configured channel: {configured_channel.mention}",
                        ephemeral=True,
                    )
                else:
                    await interaction.response.send_message(
                        f"This command can only be used in the configured channel (ID: {configured_channel_id}), but that channel seems to no longer exist. Please use `/usechannel` to set a new channel.",
                        ephemeral=True,
                    )
            else:
                await interaction.response.send_message(
                    "No channel has been configured for commands in this server. Please use `/usechannel` to set one.",
                    ephemeral=True,
                )
        return is_configured

    return app_commands.check(predicate)


async def check_configured_channel(interaction: discord.Interaction) -> bool:
    guild_id = interaction.guild_id
    channel_id = interaction.channel_id
    configured_channel_id = configured_channels.get(guild_id)

    if channel_id != configured_channel_id:
        if configured_channel_id:
            configured_channel = interaction.guild.get_channel(configured_channel_id)
            if configured_channel:
                await interaction.response.send_message(
                    f"This command can only be used in the configured channel: {configured_channel.mention}",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"This command can only be used in the configured channel (ID: {configured_channel_id}), but that channel seems to no longer exist. Please use `/usechannel` to set a new channel.",
                    ephemeral=True,
                )
        else:
            await interaction.response.send_message(
                "No channel has been configured for commands in this server. Please use `/usechannel` to set one.",
                ephemeral=True,
            )
        return False
    return True


@bot.tree.command(
    name="challenge", description="Challenge another user to a samurai duel"
)
async def challenge(
    interaction: discord.Interaction, opponent: discord.Member, emoji: str = None
):

    channel_id = interaction.channel_id
    if channel_id in ongoing_matches:
        await interaction.followup.send(
            "A game is already in progress in this channel.", ephemeral=True
        )
        return

    if interaction.user == opponent:
        await interaction.followup.send("You can't challenge yourself!", ephemeral=True)
        return

    if channel_id not in challenges:
        challenges[channel_id] = {}

    challenger_id = interaction.user.id
    opponent_id = opponent.id

    # Check if this is an acceptance of an existing challenge
    # if (
    #     challenger_id in challenges[channel_id]
    #     and opponent_id in challenges[channel_id][challenger_id]
    # ):
    #     # Start the game
    #     logger.debug(
    #         f"Starting game between {interaction.user.name} and {opponent.name}"
    #     )
    #     print("This is normal invocation")

    #     interaction.send(
    #         "Duel confirmed! This msg is logistically required :)", ephemeral=True
    #     )

    #     opponent_interaction = challenges[channel_id][challenger_id][
    #         1
    #     ]  # Get the stored interaction
    #     game_state = GameState(
    #         opponent,
    #         interaction.user,
    #         interaction.channel,
    #         opponent_interaction,
    #         interaction,
    #         challenges[channel_id][challenger_id][2],
    #         emoji,
    #     )
    #     ongoing_matches[channel_id] = game_state
    #     del challenges[channel_id][challenger_id]
    #     await game_state.run_until_end()
    #     del ongoing_matches[channel_id]
    # elif (
    if (
        opponent_id in challenges[channel_id]
        and challenger_id in challenges[channel_id][opponent_id]
    ):
        await interaction.response.send_message(
            "Duel confirmed! This msg is logistically required :)", ephemeral=True
        )
        # await interaction.response.defer(ephemeral=True)
        print("This is reverse invocation")
        # Start the game (reverse order because the original challenger is now the opponent)
        challenger_interaction = challenges[channel_id][opponent_id][
            1
        ]  # Get the stored interaction
        game_state = GameState(
            opponent,
            interaction.user,
            interaction.channel,
            challenger_interaction,
            interaction,
            challenges[channel_id][opponent_id][2],
            emoji,
        )
        ongoing_matches[channel_id] = game_state
        del challenges[channel_id][opponent_id]
        await game_state.run_until_end()
        del ongoing_matches[channel_id]
    else:
        # This is a new challenge
        challenges[channel_id][challenger_id] = (
            opponent_id,
            interaction,
            emoji,
        )  # Store the challenger's interaction and emoji
        await interaction.response.send_message(
            f"{interaction.user.mention} has challenged {opponent.mention} to a samurai duel! {opponent.mention}, use /challenge to accept.",
            ephemeral=False,
        )
    logger.debug(f"Challenge command completed. Current challenges: {challenges}")


# @bot.tree.command(name="forfeit", description="Forfeit the current game")
# @is_configured_channel()
# async def forfeit(interaction: discord.Interaction):
#     channel_id = interaction.channel_id
#     if channel_id not in ongoing_matches:
#         await interaction.response.send_message(
#             "There is no ongoing game in this channel.", ephemeral=True
#         )
#         return

#     game = ongoing_matches[channel_id]
#     if interaction.user not in [game.player1, game.player2]:
#         await interaction.response.send_message(
#             "You are not part of the ongoing game.", ephemeral=True
#         )
#         return

#     winner = game.player2 if interaction.user == game.player1 else game.player1
#     forfeit_message = f"{interaction.user.mention} has forfeited the match."

#     # Update stats
#     db_handler.update_stats(winner.id, interaction.guild.id, True)
#     db_handler.update_stats(interaction.user.id, interaction.guild.id, False)

#     # End the game
#     await game.end_game(forfeit_message)

#     # Clean up
#     del ongoing_matches[channel_id]
#     if channel_id in player_timeouts:
#         for task in player_timeouts[channel_id].values():
#             task.cancel()
#         del player_timeouts[channel_id]

#     await interaction.response.send_message(
#         "You have forfeited the game.", ephemeral=True
#     )


@bot.tree.command(name="stats", description="Check your duel statistics")
async def stats(interaction: discord.Interaction):
    await check_configured_channel(interaction)
    user_stats = db_handler.get_stats(interaction.user.id, interaction.guild.id)
    total_games = user_stats["wins"] + user_stats["losses"]
    win_rate = (user_stats["wins"] / total_games * 100) if total_games > 0 else 0

    await interaction.response.send_message(
        f"Duel Statistics for {interaction.user.mention}:\n"
        f"Wins: {user_stats['wins']}\n"
        f"Losses: {user_stats['losses']}\n"
        f"Total Games: {total_games}\n"
        f"Win Rate: {win_rate:.2f}%"
    )


# @bot.event
# async def on_interaction(interaction: discord.Interaction):
#     if interaction.type == discord.InteractionType.component:
#         custom_id = interaction.data["custom_id"]
#         if custom_id.startswith("move_"):
#             await interaction.response.defer(ephemeral=True)

#             if interaction.channel_id == configured_channels.get(interaction.guild_id):
#                 try:
#                     move = custom_id.split("_", 1)[1]
#                     channel_id = interaction.channel_id
#                     if channel_id in ongoing_matches:
#                         game = ongoing_matches[channel_id]
#                         await game.make_move(interaction.user, move)
#                     else:
#                         await interaction.followup.send(
#                             "There is no ongoing game in this channel.", ephemeral=True
#                         )
#                 except Exception as e:
#                     logging.exception("Error handling move")
#                     await interaction.followup.send(
#                         f"An error occurred: {str(e)}", ephemeral=True
#                     )
#             else:
#                 await interaction.followup.send(
#                     "This command can only be used in the configured channel.",
#                     ephemeral=True,
#                 )


# Run the bot
bot.run(os.environ.get("DUELBOT_TOKEN"))
