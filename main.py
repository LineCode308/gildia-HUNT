from flask import Flask





import os
import discord
import asyncio

from dotenv import load_dotenv
from discord.ext import commands

# =========================================================
# KONFIGURACJA
# =========================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("Nie znaleziono DISCORD_TOKEN w pliku .env!")

# POWITANIA
WELCOME_CHANNEL_ID = 1567940953040232551
AUTO_ROLE_ID = 1568694462601887956
GUILD_CHANNEL_ID = 123456789012345678  # UZUPEŁNIJ ID

# TICKETY
TICKET_PANEL_CHANNEL_ID = 1568699441488076832
TICKET_CATEGORY_ID = 123456789012345678  # UZUPEŁNIJ ID
STAFF_ROLE_ID = 123456789012345678  # UZUPEŁNIJ ID

# KOLOR EMBEDÓW
COLOR = discord.Color.from_rgb(0, 0, 0)


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# EMBED POWITALNY
# =========================================================

def create_welcome_embed(member):

    embed = discord.Embed(
        title="GILDIA HUNT × POWITANIA",
        description=(
            f"> <:czlonek:1567976307302735902> Witaj na **GILDI HUNT!** "
            f"Jesteś **{member.guild.member_count} osobą na serwerze**\n\n"

            f"> <:super:1567984387457421473> Miło Cię widzieć na HUNT!\n"
            f"> Mamy nadzieję, że nie opuścisz nas i zostaniesz na dłużej!\n\n"

            f"**> <:regulamin:1567980863826690159> "
            f"Zapoznaj się z regulaminem.**\n\n"

            f"**> <:ticket:1567981310788509786> "
            f"Aby dołączyć do naszej gildii, stwórz ticket na kanale** "
            f"<#{GUILD_CHANNEL_ID}>."
        ),
        color=COLOR
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="HUNT • Witamy na serwerze")

    return embed


# =========================================================
# ZAMYKANIE TICKETÓW
# =========================================================

class CloseTicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ZAMKNIJ TICKET",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="hunt_close_ticket"
    )
    async def close_ticket(self, interaction, button):

        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)

        is_staff = (
            interaction.user.guild_permissions.administrator
            or (
                staff_role is not None
                and staff_role in interaction.user.roles
            )
        )

        is_owner = (
            interaction.channel.topic
            == f"ticket_owner:{interaction.user.id}"
        )

        if not is_staff and not is_owner:
            await interaction.response.send_message(
                "❌ Nie masz uprawnień do zamknięcia ticketu.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Ticket zostanie zamknięty za 3 sekundy."
        )

        await asyncio.sleep(3)

        await interaction.channel.delete(
            reason=f"Ticket zamknięty przez {interaction.user}"
        )


# =========================================================
# TWORZENIE TICKETU
# =========================================================

async def create_ticket(interaction, ticket_type, answers):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ Nie znaleziono serwera.",
            ephemeral=True
        )
        return

    category = guild.get_channel(TICKET_CATEGORY_ID)
    staff_role = guild.get_role(STAFF_ROLE_ID)

    if category is None or not isinstance(category, discord.CategoryChannel):
        await interaction.response.send_message(
            "❌ Nie znaleziono kategorii ticketów. Sprawdź TICKET_CATEGORY_ID.",
            ephemeral=True
        )
        return

    # SPRAWDZANIE OTWARTYCH TICKETÓW

    for existing_channel in category.channels:

        if existing_channel.topic == f"ticket_owner:{interaction.user.id}":
            await interaction.response.send_message(
                f"❌ Masz już otwarty ticket: {existing_channel.mention}",
                ephemeral=True
            )
            return

    # UPRAWNIENIA KANAŁU

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),

        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )
    }

    bot_member = guild.get_member(bot.user.id)

    if bot_member:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            read_message_history=True
        )

    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )

    username = interaction.user.name.lower().replace(" ", "-")

    await interaction.response.defer(ephemeral=True)

    try:
        channel = await guild.create_text_channel(
            name=f"ticket-{username}"[:90],
            category=category,
            topic=f"ticket_owner:{interaction.user.id}",
            overwrites=overwrites
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Bot nie ma uprawnień do tworzenia kanałów.",
            ephemeral=True
        )
        return

    except discord.HTTPException as e:
        await interaction.followup.send(
            f"❌ Błąd tworzenia ticketu: {e}",
            ephemeral=True
        )
        return

    # EMBED TICKETU

    embed = discord.Embed(
        title=f"GILDIA HUNT × {ticket_type.upper()}",
        description=(
            f"👤 **Użytkownik:** {interaction.user.mention}\n"
            f"📂 **Kategoria:** {ticket_type}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{answers}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔧 Administracja odpowie, gdy będzie dostępna."
        ),
        color=COLOR
    )

    embed.set_footer(
        text=f"HUNT • Ticket użytkownika {interaction.user}"
    )

    await channel.send(
        content=(
            f"{interaction.user.mention} "
            f"{staff_role.mention if staff_role else ''}"
        ),
        embed=embed,
        view=CloseTicketView(),
        allowed_mentions=discord.AllowedMentions(
            users=True,
            roles=True
        )
    )

    await interaction.followup.send(
        f"✅ Twój ticket został utworzony: {channel.mention}",
        ephemeral=True
    )


# =========================================================
# FORMULARZ REKRUTACJI
# =========================================================

class RekrutacjaModal(discord.ui.Modal, title="Rekrutacja HUNT"):

    dlaczego = discord.ui.TextInput(
        label="Dlaczego chcesz do nas dołączyć?",
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    pvp = discord.ui.TextInput(
        label="Jak oceniasz swoje PvP?",
        max_length=200
    )

    wiek_premium = discord.ui.TextInput(
        label="Ile masz lat i czy masz Minecraft Premium?",
        placeholder="Np. 16 lat, tak",
        max_length=100
    )

    main = discord.ui.TextInput(
        label="Jaki tryb mainujesz?",
        max_length=150
    )

    gildie = discord.ui.TextInput(
        label="Byłeś w innych gildiach? Jakich?",
        style=discord.TextStyle.paragraph,
        max_length=300
    )

    async def on_submit(self, interaction):

        answers = (
            f"👤 **Dlaczego HUNT?**\n{self.dlaczego.value}\n\n"
            f"⚔️ **Ocena PvP:**\n{self.pvp.value}\n\n"
            f"🎮 **Wiek i Minecraft Premium:**\n{self.wiek_premium.value}\n\n"
            f"🎯 **Mainowany tryb:**\n{self.main.value}\n\n"
            f"🏆 **Poprzednie gildie:**\n{self.gildie.value}"
        )

        await create_ticket(
            interaction,
            "Rekrutacja",
            answers
        )


# =========================================================
# FORMULARZ SOJUSZU
# =========================================================

class SojuszModal(discord.ui.Modal, title="Sojusz HUNT"):

    tag = discord.ui.TextInput(
        label="Jaki TAG posiada wasza gildia?",
        max_length=50
    )

    czlonkowie = discord.ui.TextInput(
        label="Ilu członków liczy wasza gildia?",
        max_length=50
    )

    lider = discord.ui.TextInput(
        label="Czy jesteś liderem gildii?",
        placeholder="Jeśli nie, zaproś lidera do ticketu",
        max_length=100
    )

    serwery = discord.ui.TextInput(
        label="Na jakich serwerach gracie?",
        max_length=200
    )

    pvp = discord.ui.TextInput(
        label="Jak oceniacie swoje PvP gildyjne?",
        style=discord.TextStyle.paragraph,
        max_length=300
    )

    async def on_submit(self, interaction):

        answers = (
            f"🏷️ **TAG gildii:**\n{self.tag.value}\n\n"
            f"👥 **Liczba członków:**\n{self.czlonkowie.value}\n\n"
            f"👑 **Czy jesteś liderem?**\n{self.lider.value}\n\n"
            f"🎮 **Serwery:**\n{self.serwery.value}\n\n"
            f"⚔️ **PvP gildyjne:**\n{self.pvp.value}"
        )

        await create_ticket(
            interaction,
            "Sojusz",
            answers
        )


# =========================================================
# FORMULARZ PYTANIA
# =========================================================

class PytanieModal(discord.ui.Modal, title="Pytanie HUNT"):

    pytanie = discord.ui.TextInput(
        label="Opisz swoje pytanie",
        placeholder="Co chciałbyś wiedzieć?",
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    problem = discord.ui.TextInput(
        label="Opisz swój problem",
        placeholder="Opisz dokładnie swój problem...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000
    )

    async def on_submit(self, interaction):

        answers = (
            f"❓ **Pytanie:**\n{self.pytanie.value}\n\n"
            f"🔧 **Opis problemu:**\n"
            f"{self.problem.value or 'Nie podano'}"
        )

        await create_ticket(
            interaction,
            "Pytanie",
            answers
        )


# =========================================================
# MENU WYBORU TICKETÓW
# =========================================================

class TicketSelect(discord.ui.Select):

    def __init__(self):

        options = [
            discord.SelectOption(
                label="Rekrutacja",
                description="Chcesz dołączyć do gildii HUNT?",
                emoji="⚔️",
                value="rekrutacja"
            ),

            discord.SelectOption(
                label="Sojusz",
                description="Chcesz nawiązać współpracę z HUNT?",
                emoji="🤝",
                value="sojusz"
            ),

            discord.SelectOption(
                label="Pytanie",
                description="Masz pytanie lub problem?",
                emoji="❓",
                value="pytanie"
            )
        ]

        super().__init__(
            placeholder="🎫 Wybierz kategorię ticketu...",
            options=options,
            custom_id="hunt_ticket_select"
        )

    async def callback(self, interaction):

        if self.values[0] == "rekrutacja":
            await interaction.response.send_modal(
                RekrutacjaModal()
            )

        elif self.values[0] == "sojusz":
            await interaction.response.send_modal(
                SojuszModal()
            )

        elif self.values[0] == "pytanie":
            await interaction.response.send_modal(
                PytanieModal()
            )


class TicketPanel(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# =========================================================
# AUTOMATYCZNY PANEL TICKETÓW
# =========================================================

async def send_ticket_panel():

    print("Przygotowywanie panelu ticketów HUNT...")

    channel = bot.get_channel(TICKET_PANEL_CHANNEL_ID)

    if channel is None:
        try:
            channel = await bot.fetch_channel(
                TICKET_PANEL_CHANNEL_ID
            )
        except discord.HTTPException as e:
            print(f"Nie znaleziono kanału ticketów: {e}")
            return

    embed = discord.Embed(
        title="🎫 GILDIA HUNT × TICKETY",
        description=(
            "Witaj w systemie ticketów **HUNT!**\n\n"
            "Potrzebujesz pomocy, chcesz dołączyć do gildii "
            "lub nawiązać sojusz? Wybierz kategorię poniżej.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⚔️ **Rekrutacja**\n"
            "Chcesz dołączyć do gildii HUNT?\n\n"
            "🤝 **Sojusz**\n"
            "Chcesz nawiązać współpracę z naszą gildią?\n\n"
            "❓ **Pytanie**\n"
            "Masz pytanie lub problem?\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📩 Administracja odpowie, gdy będzie dostępna."
        ),
        color=COLOR
    )

    embed.set_footer(text="HUNT • System ticketów")

    try:
        await channel.send(
            embed=embed,
            view=TicketPanel()
        )

        print("Panel ticketów HUNT został wysłany!")

    except discord.HTTPException as e:
        print(f"Błąd wysyłania panelu: {e}")


# =========================================================
# START BOTA
# =========================================================

@bot.event
async def setup_hook():

    bot.add_view(TicketPanel())
    bot.add_view(CloseTicketView())


@bot.event
async def on_ready():

    print(f"Bot {bot.user} działa!")
    print("System HUNT: powitania, rangi i tickety aktywne.")

    if not getattr(bot, "ticket_panel_sent", False):
        await send_ticket_panel()
        bot.ticket_panel_sent = True


# =========================================================
# AUTOMATYCZNA RANGA + POWITANIE
# =========================================================

@bot.event
async def on_member_join(member):

    # AUTOMATYCZNE NADAWANIE RANGI

    role = member.guild.get_role(AUTO_ROLE_ID)

    if role is not None:
        try:
            await member.add_roles(
                role,
                reason="Automatyczna ranga po wejściu na serwer HUNT"
            )

            print(f"Nadano rangę {role.name}: {member}")

        except discord.Forbidden:
            print("Bot nie ma uprawnień do nadawania rangi!")

        except discord.HTTPException as e:
            print(f"Błąd nadawania rangi: {e}")

    else:
        print("Nie znaleziono rangi o podanym ID!")

    # POWITANIE

    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    if channel is None:
        try:
            channel = await bot.fetch_channel(
                WELCOME_CHANNEL_ID
            )
        except discord.HTTPException:
            print("Nie znaleziono kanału powitań!")
            return

    embed = create_welcome_embed(member)

    await channel.send(
        content=f"<:witaj:1567978044956737587> {member.mention}",
        embed=embed,
        allowed_mentions=discord.AllowedMentions(
            users=True,
            roles=False,
            everyone=False
        )
    )


# =========================================================
# KOMENDA TESTOWA POWITAŃ
# =========================================================

@bot.command(name="testpowitanie")
@commands.has_permissions(administrator=True)
async def test_powitanie(ctx):

    embed = create_welcome_embed(ctx.author)

    await ctx.send(
        content=f"<:witaj:1567978044956737587> {ctx.author.mention}",
        embed=embed,
        allowed_mentions=discord.AllowedMentions(
            users=True,
            roles=False,
            everyone=False
        )
    )


# =========================================================
# OBSŁUGA BŁĘDÓW
# =========================================================


@bot.event

async def on_command_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Nie masz uprawnień do tej komendy!"
        )

    elif isinstance(error, commands.CommandNotFound):
        return

    else:
        raise error


# =========================================================
# URUCHOMIENIE
# =========================================================

app = Flask(name)


@app.route("/")
def home():
    return "Bot Discord działa!", 200


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    server = Thread(target=run_web, daemon=True)
    server.start()


keep_alive()


if name == "main":

    if TOKEN == "TWÓJ_TOKEN":
        print("USTAW TOKEN BOTA W ZMIENNEJ TOKEN!")

    bot.run(TOKEN)

