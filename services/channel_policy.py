"""Channel routing for the designated guild; other guilds are unchanged."""
from discord import app_commands

TARGET_GUILD_ID = 1107219721570496542
MUSIC_CHANNEL_ID = 1567934204149244094
VICTIMS_CHANNEL_ID = 1118238037676130336
MUSIC_COMMANDS = frozenset({
    "play", "wave", "wave_stop", "pause", "next", "queue", "nowplaying",
    "remove", "shuffle", "repeat", "stop", "clear", "disconnect", "playlist",
})


def routed_channel(guild, fallback, *, victims=False):
    if guild is None or guild.id != TARGET_GUILD_ID:
        return fallback
    channel_id = VICTIMS_CHANNEL_ID if victims else MUSIC_CHANNEL_ID
    channel = guild.get_channel(channel_id)
    if channel is None:
        raise RuntimeError(f"Канал <#{channel_id}> недоступен. Обратитесь к администратору.")
    return channel


async def check_channel(interaction, *, victims=False):
    if interaction.guild_id != TARGET_GUILD_ID:
        return True
    channel_id = VICTIMS_CHANNEL_ID if victims else MUSIC_CHANNEL_ID
    if interaction.channel_id == channel_id:
        return True
    topic = "Команды рубрики «Жертвы движухи»" if victims else "Музыкальные команды и кнопки"
    send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
    await send(f"{topic} доступны только в <#{channel_id}>. Перейдите в этот канал.", ephemeral=True)
    return False


class ChannelCommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction):
        name = (interaction.data or {}).get("name", "")
        if name in MUSIC_COMMANDS:
            return await check_channel(interaction)
        if name in {"victims", "victims_setup", "victims_disable"}:
            return await check_channel(interaction, victims=True)
        return True
