import discord
from discord.ext import commands
from discord import app_commands
import random
from labyrinth2.game import active_rooms

class RollCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Hodí kostkami pro rozdělení kapacity dveří")
    async def roll(self, interaction: discord.Interaction, steny: int):
        room_view = active_rooms.get(interaction.channel_id)
        
        # Pokud není aktivní místnost, uděláme jen obyčejný hod
        if not room_view:
            rolls = [random.randint(1, steny) for _ in range(4)]
            embed = discord.Embed(
                title="🎲 Volný hod",
                description=f"Padla čísla: **{', '.join(map(str, rolls))}**",
                color=0x2B2D31
            )
            await interaction.response.send_message(embed=embed)
            return
            
        if interaction.user not in room_view.players:
            await interaction.response.send_message("*Nejsi v této místnosti!*", ephemeral=True)
            return
            
        # Hodíme 4 kostkami s daným počtem stěn
        rolls = [random.randint(1, steny) for _ in range(4)]
        
        embed = discord.Embed(
            title="🎲 Výsledek hodu na podstavci",
            description=f"**{interaction.user.display_name}** hodil kostkami!\n\n"
                        f"**Padla čísla:** {', '.join(map(str, rolls))}\n"
                        f"*Magický mechanismus podstavce rozděluje kapacitu do dveří...*",
            color=0x00FF00
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Aktualizujeme místnost - přidáme tlačítka s dveřmi
        room_view.apply_roll_and_show_doors(rolls)
        
        if room_view.message:
            room_embed = room_view._create_embed()
            room_embed.add_field(name="Dveře se otevřely", value="Cesta dál je volná. Jakým směrem se vydáte?", inline=False)
            await room_view.message.edit(embed=room_embed, view=room_view)
            
        # Místnost už nečeká na hod
        del active_rooms[interaction.channel_id]

async def setup(bot):
    await bot.add_cog(RollCog(bot))
