import discord
from discord.ext import commands
import asyncio
import re
import aiosqlite as sqlite

class LilyMain(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        self.db: sqlite.Connection = None
        self.emoji_strip = None
        super().__init__(command_prefix='?',intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

        self.db = sqlite.connect("storage.db")

        # Schema design.
        await self.db.execute("CREATE TABLE IF NOT EXISTS roles (guild_id INTEGER, role_id INTEGER, role_emoji TEXT)")

        # Regex to remove unicode emoji
        self.emoji_strip = re.compile("[\U00010000-\U0010ffff]", flags=re.UNICODE)

        
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if after.bot:
            return

        if before.roles == after.roles:
            return

        if before.top_role == after.top_role:
            return


        base_name = self.emoji_strip.sub(after.display_name, "").strip()

        # If an new role is added, we update the member's display name to mimic
        if after.top_role > before.top_role:

            async with self.db.execute(
                "SELECT role_emoji FROM roles WHERE guild_id = ? AND role_id = ?",
                (after.guild.id, after.top_role.id)
            ) as cursor:
                row = await cursor.fetchone()

            if not row or not row[0]:

                if after.display_name != base_name:
                    try:
                        await after.edit(nick=base_name)
                    except (discord.Forbidden, discord.HTTPException):
                        pass

                return


            emoji: str = row[0]
            new_nick = f"{base_name} {emoji}"

            if after.display_name == new_nick:
                return

            try:
                await after.edit(nick=new_nick)
            except (discord.Forbidden, discord.HTTPException):
                pass


    async def on_ready(self):
        print(f"Logged in as {self.user}")

bot = LilyMain()

@commands.has_permissions(administrator=True)
@bot.hybrid_command(name="add_role_emoji", description="Add a role emoji to a role")
async def add_role_emoji(ctx: commands.Context, role: discord.Role, icon: str) -> None:
    try:
        await bot.db.execute("INSERT INTO roles (guild_id, role_id, role_emoji) VALUES (?, ?, ?)", (ctx.guild.id, role.id, icon))
        await bot.db.commit()
        await ctx.reply("Emoji Updated")
    except Exception as e:
        await ctx.reply("An Unknown Error Occured!", delete_after=7)

@commands.cooldown(type=commands.BucketType.user, rate=5)
async def role_list(ctx: commands.Context):
    try:
        role_ids: str = 'None'
        role_emojis: str = 'None'
        async with bot.db.execute("SELECT role_id, role_emoji FROM roles WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
            rows = cursor.fetchall()
            if rows:
                for role_id, role_emoji in rows:
                    role_ids += f'<@&{role_id}>\n'
                    role_emoji += f'{role_emoji}\n'
        embed = discord.Embed(title='Roles and their Badges')
        embed.add_field(name='Roles', value=role_ids)
        embed.add_field(name='Badges', value=role_emojis)

        await ctx.reply(embed=embed)

    except Exception as e:
        await ctx.reply("An Unknown Error Occured!", delete_after=7)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("Missing Permission!", delete_after=5)
    pass

async def main():
    await bot.start("YOUR_BOT_TOKEN")

if __name__ == "__main__":
    asyncio.run(main())