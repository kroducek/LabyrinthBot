import discord
import random

class RoomView(discord.ui.View):
    def __init__(self, players: list[discord.Member], room_name: str = "A1"):
        super().__init__(timeout=None)
        self.players = players
        self.room_name = room_name
        self.choices = {}  # user_id -> door_index
        self.doors = []    # list of capacities
        
    def _create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🚪 Místnost [{self.room_name}]",
            description=(
                f"*Ocitáte se v temné, chladné místnosti {self.room_name}.*\n"
                "*Vzduch je těžký a ticho přerušuje jen vaše dýchání.*\n\n"
                "Uprostřed místnosti stojí malý kamenný podstavec s vyrytými symboly. "
                "Zdá se, že mechanismus dveří je napojen na tento podstavec a čeká na vaši interakci.\n\n"
                f"**Hráči zde ({len(self.players)}):** " + ", ".join(p.display_name for p in self.players)
            ),
            color=0x2B2D31
        )
        if self.doors:
            embed.add_field(name="Dveře se otevřely", value="Cesta dál je volná. Jakým směrem se vydáte?", inline=False)
            
        return embed

    @discord.ui.button(label="🎲 Hodit kostkami na podstavci", style=discord.ButtonStyle.primary, custom_id="lab2_roll")
    async def roll_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
            return
            
        # Mechanika 4d(počet hráčů v místnosti)
        sides = max(1, len(self.players))
        self.doors = [random.randint(1, sides) for _ in range(4)]
        
        # Odebrat tlačítko pro hod
        self.remove_item(button)
        
        colors = ["🔴 Červené", "🔵 Modré", "🟢 Zelené", "🟡 Žluté"]
        for i, cap in enumerate(self.doors):
            btn = discord.ui.Button(
                label=f"{colors[i]} [{cap}]",
                style=discord.ButtonStyle.secondary,
                custom_id=f"lab2_door_{i}"
            )
            btn.callback = self.make_door_callback(i)
            self.add_item(btn)
            
        await interaction.response.edit_message(embed=self._create_embed(), view=self)

    def make_door_callback(self, door_index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user not in self.players:
                await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
                return
                
            if interaction.user.id in self.choices:
                await interaction.response.send_message("*Své rozhodnutí už jsi učinil!*", ephemeral=True)
                return
                
            if self.doors[door_index] <= 0:
                await interaction.response.send_message("*Tato cesta je už plná! Musíš jinudy.*", ephemeral=True)
                return
                
            self.doors[door_index] -= 1
            self.choices[interaction.user.id] = door_index
            
            # Aktualizace kapacity na tlačítku
            for item in self.children:
                if getattr(item, "custom_id", "") == f"lab2_door_{door_index}":
                    # Nahradíme číslo v závorce novou kapacitou
                    base_label = item.label.split('[')[0]
                    item.label = f"{base_label}[{self.doors[door_index]}]"
                    if self.doors[door_index] == 0:
                        item.disabled = True
                    break
                    
            if len(self.choices) == len(self.players):
                # Všichni prošli -> v ostré verzi by se tu hráči rozdělili podle výběru
                # Pro účely testu procházení je všechny hodíme společně do další místnosti
                next_room = f"{random.choice('ABCDEFGH')}{random.randint(1, 8)}"
                next_view = RoomView(self.players, next_room)
                
                await interaction.response.edit_message(
                    content=f"*Všichni prošli dveřmi a nechali místnost {self.room_name} za sebou...*", 
                    embed=None, view=None
                )
                await interaction.channel.send(embed=next_view._create_embed(), view=next_view)
            else:
                # Někdo ještě neprošel, jen upravíme tlačítka
                await interaction.response.edit_message(view=self)
                
        return callback
