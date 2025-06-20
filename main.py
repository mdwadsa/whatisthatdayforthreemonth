import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from aiohttp import web
from datetime import datetime, timedelta
import urllib.parse
import yt_dlp as youtube_dl

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.voice_states = True
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
# ------------------- SoundCloud ---------------------
OWNER_ID = 948531215252742184

# ملف حفظ الأغاني
SONGS_FILE = "songs.json"

# إعدادات yt_dlp
ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]
}

# تحميل البيانات من ملف JSON
def load_songs():
    if os.path.exists(SONGS_FILE):
        try:
            with open(SONGS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # الملف فاضي أو تالف، يرجع قاموس فارغ
            return {}
    return {}

# حفظ البيانات
def save_songs(songs):
    with open(SONGS_FILE, 'w') as f:
        json.dump(songs, f, indent=4)

saved_songs = load_songs()

# التحقق من صلاحيات المستخدم
def is_owner(ctx):
    return ctx.author.id == OWNER_ID

# أمر !join
@bot.command()
@commands.check(is_owner)
async def join(ctx, channel_id: int):
    channel = bot.get_channel(channel_id)
    if isinstance(channel, discord.VoiceChannel):
        await channel.connect()
        await ctx.send(f"✅ انضممت إلى الروم الصوتي: {channel.name}")
    else:
        await ctx.send("❌ لم أتمكن من العثور على روم صوتي بهذا المعرف.")

# أمر !play
@bot.command()
@commands.check(is_owner)
async def play(ctx, name_or_url):
    voice_client = ctx.guild.voice_client

    if not voice_client:
        await ctx.send("❌ يجب أن أكون في روم صوتي أولاً. استخدم !join.")
        return

    url = saved_songs.get(name_or_url, name_or_url)

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
        except Exception as e:
            await ctx.send(f"❌ حدث خطأ أثناء جلب الرابط: {e}")
            return

    voice_client.stop()
    voice_client.play(discord.FFmpegPCMAudio(audio_url), after=lambda e: print(f"انتهى التشغيل: {e}"))

    await ctx.send(f"🎵 جاري تشغيل: {info.get('title', 'مقطع صوتي')}")

# أمر !stop
@bot.command()
@commands.check(is_owner)
async def stop(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("⏹️ تم إيقاف التشغيل.")
    else:
        await ctx.send("❌ لا يوجد شيء يعمل حالياً.")

# أمر !name <url> <اسم>
@bot.command()
@commands.check(is_owner)
async def name(ctx, url, name):
    saved_songs[name] = url
    save_songs(saved_songs)
    await ctx.send(f"✅ تم حفظ الأغنية باسم: `{name}`")

# أمر !leave
@bot.command()
@commands.check(is_owner)
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 تم الخروج من الروم الصوتي.")
    else:
        await ctx.send("❌ لست متصلاً بأي روم صوتي.")

# ------------------- رتب تلقائيه ------------------------
@bot.event
async def on_member_join(member):
    role_id = 1384445062183780352  # ID الرتبة
    role = member.guild.get_role(role_id)
    if role:
        try:
            await member.add_roles(role)
            print(f"🎉 تم إعطاء الرتبة {role.name} للعضو {member.name}")
        except Exception as e:
            print(f"❌ خطأ في إعطاء الرتبة: {e}")
    else:
        print("⚠️ لم يتم العثور على الرتبة")
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
# -------------------- رتب مخفيه -------------------------

OWNER_ID = 948531215252742184
CODES_FILE = "codes.json"

# تحميل الرموز من ملف
def load_codes():
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, "r") as f:
            return json.load(f)
    return {}

# حفظ الرموز
def save_codes():
    with open(CODES_FILE, "w") as f:
        json.dump(codes, f)

codes = load_codes()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def generate(ctx, role: discord.Role, code: str):
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ هذا الأمر فقط لصاحب البوت.")
        return
    if code in codes:
        await ctx.send("⚠️ الرمز موجود مسبقاً.")
        return
    codes[code] = role.id
    save_codes()
    await ctx.send(f"✅ تم إنشاء الرمز `{code}` للرتبة **{role.name}**.")

@bot.command()
async def redeem(ctx, code: str):
    if code not in codes:
        await ctx.send("❌ الرمز غير صالح أو تم استخدامه.")
        return
    role_id = codes.pop(code)
    save_codes()
    role = ctx.guild.get_role(role_id)
    if role is None:
        await ctx.send("❌ لم يتم العثور على الرتبة.")
        return
    await ctx.author.add_roles(role)
    await ctx.send(f"✅ تم إعطاؤك رتبة **{role.name}**.")

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

# --------------------- Shows-------------------------
@bot.command(name="anime")
async def anime(ctx, *, name: str):
    search_url = f"https://witanime.cyou/?search_param=animes&s={name.replace(' ', '+')}"
    embed = discord.Embed(
        title="🔎 نتيجة البحث عن أنمي",
        description=f"🎌 اسم الأنمي: `{name}`\n🔗 [اضغط هنا لعرض النتائج]({search_url})",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(name="movie")
async def movie(ctx, *, name: str):
    formatted_name = name.lower().replace(" ", "-")
    search_url = f"https://www.faselhds.care/movies/1فيلم-{formatted_name}"
    embed = discord.Embed(
        title="🎬 رابط الفيلم",
        description=f"🎞️ اسم الفيلم: `{name}`\n🔗 [مشاهدة الفيلم]({search_url})",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="Series")
async def series(ctx, *, series_name: str):
    # استبدال الفراغات بـ +
    formatted_name = series_name.replace(" ", "+")

    url = f"https://ze0shqhjbe.sbs/?s={formatted_name}"

    embed = discord.Embed(
        title=f"نتائج بحث عن المسلسل: {series_name}",
        description=f"[اضغط هنا لمشاهدة البحث في EgyDead]({url})",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)

#---------------------عرض الأوامر-----------------------
@bot.command(name="اوامر")
async def all_commands(ctx):
    embed = discord.Embed(
        title="📜 قائمة أوامر البوت",
        description="جميع الأوامر المتوفرة حالياً:",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="🔧 أوامر الإدارة:",
        value=(
            "`!ban @عضو [سبب]`\n"
            "`!unban user_id`\n"
            "`!timeout @عضو مدة_بالثواني`\n"
            "`!untimeout @عضو`\n"
            "`!مسح عدد`\n"
            "`!generate الرتبة`"
        ),
        inline=False
    )

    embed.add_field(
        name="📥 أوامر الرسائل الخاصة:",
        value=(
            "`!dm @عضو رسالة`\n"
            "`!all_dm رسالة`"
        ),
        inline=False
    )

    embed.add_field(
        name="🕒 تسجيل الدخول والخروج:",
        value=(
            "`!login`\n"
            "`!logout`\n"
            "`!show @عضو`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎫 نظام التكتات:",
        value="`!setup_Ticket` (واجهة إنشاء التكت)",
        inline=False
    )

    embed.add_field(
        name="👀 مراقبة الحالة:",
        value="`!online_ping user_id`",
        inline=False
    )

    embed.add_field(
        name="🧪 حالة البوت:",
        value="`!areyouhere?`",
        inline=False
    )

    embed.add_field(
        name="🎬 أوامر البحث:",
        value=(
            "`!anime اسم_الأنمي`\n"
            "`!movie اسم_الفيلم`\n"
            "`!Series اسم_المسلسل_بـ_شرطة_سفلية`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎖 أوامر الأعضاء:",
        value="`!redeem الرمز`",
        inline=False
    )

    await ctx.send(embed=embed)

# --------------------صلاحيات الأوامر --------------------
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
