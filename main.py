import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from aiohttp import web
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.presences = True  # لمراقبة الحالة

bot = commands.Bot(command_prefix="!", intents=intents)

# ملفات لتخزين البيانات
CODES_FILE = "codes.json"
USERS_FILE = "users.json"

def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    online_ping_task.start()

# ------------------- online_ping --------------------
online_watchlist = {}  # { user_id: last_status }

@bot.command(name="online_ping")
async def online_ping(ctx, user_id: int):
    user = ctx.guild.get_member(user_id)
    if not user:
        await ctx.send("❌ ما لقيت العضو بالسيرفر.")
        return

    online_watchlist[user_id] = None
    await ctx.send(f"✅ بدأ متابعة حالة العضو {user.mention}")

@tasks.loop(seconds=30)
async def online_ping_task():
    guilds = bot.guilds
    for guild in guilds:
        for user_id in list(online_watchlist.keys()):
            member = guild.get_member(user_id)
            if not member:
                online_watchlist.pop(user_id)
                continue
            current_status = member.status
            last_status = online_watchlist.get(user_id)
            if current_status != last_status:
                online_watchlist[user_id] = current_status
                owner = guild.owner
                if current_status == discord.Status.online:
                    try:
                        await owner.send(f"✅ العضو {member.name} صار **اونلاين**.")
                    except:
                        pass
                elif current_status == discord.Status.offline:
                    try:
                        await owner.send(f"⚠️ العضو {member.name} صار **اوفلاين**.")
                    except:
                        pass

# -------------------- dm لشخص محدد ------------------
@bot.command(name="dm")
async def dm(ctx, member: discord.Member, *, message):
    try:
        await member.send(message)
        await ctx.send(f"✅ تم إرسال الرسالة إلى {member.mention}")
    except Exception as e:
        await ctx.send(f"❌ ما قدرت أرسل الرسالة: {e}")

# -------------------- all_dm لجميع أعضاء السيرفر ------------------
@bot.command(name="all_dm")
@commands.has_permissions(administrator=True)
async def all_dm(ctx, *, message):
    members = ctx.guild.members
    count = 0
    for member in members:
        if member.bot:
            continue
        try:
            await member.send(message)
            count += 1
        except:
            pass
    await ctx.send(f"✅ تم إرسال الرسالة الخاصة لـ {count} عضو.")

# -------------------- نظام تسجيل الدخول والخروج ------------------
@bot.command(name="login")
async def login(ctx):
    if not any(role.id == 1384415026323918849 for role in ctx.author.roles):
        await ctx.send("❌ ليس لديك الصلاحية لاستخدام هذا الأمر.")
        return

    users = load_json(USERS_FILE)
    user_id = str(ctx.author.id)
    if user_id not in users:
        users[user_id] = {"login_count": 0, "last_login": None}
    users[user_id]["login_count"] += 1
    users[user_id]["last_login"] = datetime.utcnow().isoformat()
    save_json(USERS_FILE, users)

    embed = discord.Embed(
        title="تم تسجيل الدخول",
        description=f"✅ تم تسجيل دخولك بنجاح!\n📅 الوقت: {users[user_id]['last_login']}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="logout")
async def logout(ctx):
    if not any(role.id == 1384415026323918849 for role in ctx.author.roles):
        await ctx.send("❌ ليس لديك الصلاحية لاستخدام هذا الأمر.")
        return

    users = load_json(USERS_FILE)
    user_id = str(ctx.author.id)
    if user_id not in users or users[user_id]["last_login"] is None:
        await ctx.send("❌ لم تقم بتسجيل الدخول بعد.")
        return

    login_time = datetime.fromisoformat(users[user_id]["last_login"])
    delta = datetime.utcnow() - login_time
    embed = discord.Embed(
        title="تم تسجيل الخروج",
        description=f"❌ تم تسجيل خروجك بنجاح!\n🕒 مدة تسجيل الدخول: {delta}",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

    users[user_id]["last_login"] = None
    save_json(USERS_FILE, users)

@bot.command(name="show")
async def show(ctx, member: discord.Member):
    if ctx.author.id != 948531215252742184:
        await ctx.send("❌ ليس لديك الصلاحية لاستخدام هذا الأمر.")
        return

    users = load_json(USERS_FILE)
    user_id = str(member.id)
    if user_id not in users or users[user_id]["last_login"] is None:
        await ctx.send(f"❌ العضو {member.mention} لم يقم بتسجيل الدخول بعد.")
        return

    login_time = datetime.fromisoformat(users[user_id]["last_login"])
    delta = datetime.utcnow() - login_time
    embed = discord.Embed(
        title=f"بيانات تسجيل الدخول للعضو {member.name}",
        description=f"📅 آخر تسجيل دخول: {login_time.strftime('%d/%m/%Y')}\n🕒 مدة تسجيل الدخول: {delta}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# -------------------- مسح رسائل --------------------
@bot.command(name="مسح")
@commands.has_permissions(administrator=True)
async def مسح(ctx, num: int):
    await ctx.channel.purge(limit=num)
    await ctx.send(f"✅ تم مسح {num} رسالة.", delete_after=5)

# -------------------- نظام التكتات الجديد --------------------

from discord.ui import View, Button, Modal, TextInput

TICKET_CATEGORY_ID = None  # ضع هنا اي دي الفئة (category) التي تريد انشاء التكتات داخلها إذا كانت موجودة
TICKET_LOG_CHANNEL_ID = 1375074073226383482
STAFF_ROLE_ID = 1384415026323918849

TICKET_RULES_TEXT = (
    "**قوانين التكت:**\n"
    "1- الالتزام بالأسلوب.\n"
    "2- عدم السبام (كثرة المنشن).\n"
    "3- احترام الجميع داخل التكت وخارجه.\n"
)

# رسالة قوانين التكت عند الضغط على زر "قوانين التكت"
class RulesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="حسنًا", style=discord.ButtonStyle.green))

    @discord.ui.button(label="حسنًا", style=discord.ButtonStyle.green)
    async def ok_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()

# مودال لكتابة سبب الإغلاق
class CloseReasonModal(Modal, title="سبب إغلاق التكت"):
    def __init__(self, ticket_channel):
        super().__init__()
        self.ticket_channel = ticket_channel

    reason = TextInput(label="اكتب سبب الإغلاق هنا:", style=discord.TextStyle.paragraph, required=True, max_length=200)

    async def on_submit(self, interaction: discord.Interaction):
        # اغلاق التكت مع ذكر السبب
        await self.ticket_channel.delete()
        log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        embed = discord.Embed(
            title="❌ تم إغلاق التكت",
            description=f"تم إغلاق التكت #{self.ticket_channel.name} من قبل {interaction.user.mention}\n**السبب:** {self.reason.value}",
            color=discord.Color.red()
        )
        await log_channel.send(embed=embed)
        await interaction.response.send_message("✅ تم إغلاق التكت مع ذكر السبب.", ephemeral=True)

# فيو أزرار التكت
class TicketView(View):
    def __init__(self, ticket_channel, ticket_owner):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.ticket_owner = ticket_owner

    @discord.ui.button(label="إغلاق التكت", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.id != self.ticket_channel.id:
            await interaction.response.send_message("❌ هذا الزر ليس في التكت الصحيح.", ephemeral=True)
            return
        # اغلاق التكت بدون سبب
        await self.ticket_channel.delete()
        log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        embed = discord.Embed(
            title="❌ تم إغلاق التكت",
            description=f"تم إغلاق التكت #{self.ticket_channel.name} من قبل {interaction.user.mention}",
            color=discord.Color.red()
        )
        await log_channel.send(embed=embed)
        await interaction.response.send_message("✅ تم إغلاق التكت.", ephemeral=True)

    @discord.ui.button(label="إغلاق التكت مع سبب", style=discord.ButtonStyle.grey, custom_id="close_ticket_reason")
    async def close_ticket_reason(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.channel.id != self.ticket_channel.id:
            await interaction.response.send_message("❌ هذا الزر ليس في التكت الصحيح.", ephemeral=True)
            return
        modal = CloseReasonModal(self.ticket_channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="استلام التكت", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # فقط للموظفين الحاملين الرتبة المحددة
        if not any(role.id == STAFF_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ ليس لديك صلاحية استلام التكت.", ephemeral=True)
            return

        log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        embed = discord.Embed(
            title="🔵 تم استلام التكت",
            description=f"تم استلام التكت #{self.ticket_channel.name} من قبل {interaction.user.mention}",
            color=discord.Color.blue()
        )
        await log_channel.send(embed=embed)
        await interaction.response.send_message("✅ تم استلام التكت بنجاح.", ephemeral=True)

# فيو أزرار القائمة الرئيسية لانشاء التكت
class TicketSetupView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إنشاء تكت", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        author = interaction.user

        # تحقق هل لديه تكت مفتوح من قبل (مثلاً نفس الاسم)
        existing = discord.utils.get(guild.text_channels, name=f"ticket-{author.name.lower()}")
        if existing:
            await interaction.response.send_message(f"❌ لديك تكت مفتوح بالفعل: {existing.mention}", ephemeral=True)
            return

        # أنشئ التكت في نفس الفئة (إذا محدد)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        if TICKET_CATEGORY_ID:
            category = guild.get_channel(TICKET_CATEGORY_ID)
            ticket_channel = await guild.create_text_channel(f"ticket-{author.name.lower()}", overwrites=overwrites, category=category)
        else:
            ticket_channel = await guild.create_text_channel(f"ticket-{author.name.lower()}", overwrites=overwrites)

        # أرسل قوانين التكت داخل القناة
        embed = discord.Embed(
            title=f"🎫 تكت جديد لـ {author.display_name}",
            description=TICKET_RULES_TEXT,
            color=discord.Color.green()
        )
        message = await ticket_channel.send(content=f"{author.mention}", embed=embed, view=TicketView(ticket_channel, author))
        await interaction.response.send_message(f"✅ تم إنشاء التكت: {ticket_channel.mention}", ephemeral=True)

    @discord.ui.button(label="قوانين التكت", style=discord.ButtonStyle.blurple, custom_id="ticket_rules")
    async def ticket_rules_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📜 قوانين التكت",
            description=TICKET_RULES_TEXT,
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name="setup_Ticket")
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    embed = discord.Embed(
        title="نظام التكتات",
        description="اختر أحد الخيارات من الأزرار أدناه:",
        color=discord.Color.blurple()
    )
    view = TicketSetupView()
    await ctx.send(embed=embed, view=view)

# -------------------- أمر !areyouhere? لتحديث روم الحالة --------------------
STATUS_CHANNEL_ID = 1375073424300314664

@bot.command(name="areyouhere?")
async def areyouhere(ctx):
    channel = bot.get_channel(STATUS_CHANNEL_ID)
    if channel is None:
        await ctx.send("❌ لم أتمكن من العثور على قناة الحالة.")
        return

    embed = discord.Embed(
        description="! I am here",
        color=discord.Color.green()
    )
    await channel.send(embed=embed)
    await ctx.send("✅ تم إرسال رسالة الحالة.")

# -------------------- أوامر الباند والتايم أوت --------------------
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"✅ تم حظر العضو {member.mention}.")

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"✅ تم فك حظر العضو {user.mention}.")

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, duration: int, *, reason=None):
    until = discord.utils.utcnow() + timedelta(seconds=duration)
    await member.timeout(until=until, reason=reason)
    await ctx.send(f"✅ تم تقييد العضو {member.mention} لمدة {duration} ثانية.")

@bot.command(name="untimeout")
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"✅ تم رفع التقييد عن العضو {member.mention}.")

# -------------------- صلاحيات الأوامر --------------------
@bot.event
async def on_command(ctx):
    if ctx.command.name in ["dm", "all_dm", "generate"] and ctx.author.id != 948531215252742184:
        await ctx.send("❌ ليس لديك الصلاحية لاستخدام هذا الأمر.")
        raise commands.CheckFailure("لا تمتلك الصلاحية.")

    if ctx.command.name in ["show", "unban", "ban", "timeout", "untimeout"] and not any(role.id == 1384420303345680448 for role in ctx.author.roles):
        await ctx.send("❌ ليس لديك الصلاحية لاستخدام هذا الأمر.")
        raise commands.CheckFailure("لا تمتلك الصلاحية.")

# -------------------- تشغيل ويب سيرفر بسيط للحفاظ على البوت حي --------------------
PORT = int(os.getenv("PORT", 8080))  # تستخدم متغير البيئة PORT أو 8080 افتراضياً

async def handle(request):
    return web.Response(text="Bot is alive!")

async def run_webserver():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"🌐 Webserver running on port {PORT}")

async def main():
    await run_webserver()
    await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

asyncio.run(main())
