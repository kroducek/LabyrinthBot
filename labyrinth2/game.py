import discord
import random

# channel_id -> RoomView
active_rooms = {}

class RoomView(discord.ui.View):
    def __init__(self, players: list[discord.Member], room_name: str = "A1"):
        super().__init__(timeout=None)
        self.players = players
        self.room_name = room_name
        self.choices = {}  # user_id -> door_index
        self.doors = []    # list of capacities
        self.message: discord.Message = None
        
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
        return embed

    @discord.ui.button(label="🎲 Vzít kostky na podstavci", style=discord.ButtonStyle.primary, custom_id="lab2_take_dice")
    async def take_dice_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            await interaction.response.send_message("*Nejsi v této místnosti.*", ephemeral=True)
            return
            
        # Odebrat tlačítko
        self.remove_item(button)
        
        sides = max(1, len(self.players))
        
        # Odeslání oznámení do chatu
        embed = discord.Embed(
            title="🎲 Házení kostkami",
            description=f"**{interaction.user.display_name}** přistoupil k podstavci a vzal si kostky.\n\n"
                        f"👉 **Nyní použij příkaz `/roll {sides}`** pro hození 4 kostkami (se {sides} stěnami)!",
            color=0x2B2D31
        )
        
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(embed=embed)
        
        # Zaregistrovat tuto místnost jako čekající na hod
        active_rooms[interaction.channel_id] = self

    def apply_roll_and_show_doors(self, rolls: list[int]):
        self.doors = rolls
        colors = ["🔴 Červené", "🔵 Modré", "🟢 Zelené", "🟡 Žluté"]
        for i, cap in enumerate(self.doors):
            btn = discord.ui.Button(
                label=f"{colors[i]} [{cap}]",
                style=discord.ButtonStyle.secondary,
                custom_id=f"lab2_door_{i}"
            )
            btn.callback = self.make_door_callback(i)
            self.add_item(btn)

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
                    base_label = item.label.split('[')[0]
                    item.label = f"{base_label}[{self.doors[door_index]}]"
                    if self.doors[door_index] == 0:
                        item.disabled = True
                    break
                    
            if len(self.choices) == len(self.players):
                # Všichni prošli, generujeme novou místnost
                next_room = f"{random.choice('ABCDEFGH')}{random.randint(1, 8)}"
                next_view = RoomView(self.players, next_room)
                
                await interaction.response.edit_message(
                    content=f"*Všichni prošli dveřmi a nechali místnost {self.room_name} za sebou...*", 
                    embed=None, view=None
                )
                msg = await interaction.channel.send(embed=next_view._create_embed(), view=next_view)
                next_view.message = msg
            else:
                # Někdo ještě neprošel
                await interaction.response.edit_message(view=self)
                
        return callback
