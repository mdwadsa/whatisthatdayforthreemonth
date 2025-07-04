import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button
import json
import os
import asyncio
from aiohttp import web
from datetime import datetime, timedelta
import urllib.parse
import yt_dlp as youtube_dl
from gtts import gTTS
import random

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.voice_states = True
intents.presences = True  # لمراقبة الحالة

bot = commands.Bot(command_prefix="!", intents=intents)

tree = bot.tree

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
# ----------------- Bank ----------------------------
# إعدادات
OWNER_ID = 948531215252742184
DATA_FILE = "bank_data.json"
COMMAND_PREFIX = "!"

# إعداد البوت
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# ======= وظائف المساعدة =======

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def ensure_account(data, user_id):
    if str(user_id) not in data:
        data[str(user_id)] = {"balance": 0}

# ======= أوامر البنك =======

@bot.command(name="رصيد")
async def balance(ctx):
    data = load_data()
    user_id = ctx.author.id
    ensure_account(data, user_id)
    balance = data[str(user_id)]["balance"]
    await ctx.send(f"💰 رصيدك الحالي: {balance} نقطة")

@bot.command(name="ايداع")
async def deposit(ctx, amount: int):
    if amount <= 0:
        return await ctx.send("❌ لا يمكنك إيداع مبلغ أقل من أو يساوي صفر.")
    data = load_data()
    user_id = ctx.author.id
    ensure_account(data, user_id)
    data[str(user_id)]["balance"] += amount
    save_data(data)
    await ctx.send(f"✅ تم إيداع {amount} نقطة في حسابك.")

@bot.command(name="سحب")
async def withdraw(ctx, amount: int):
    if amount <= 0:
        return await ctx.send("❌ لا يمكنك سحب مبلغ أقل من أو يساوي صفر.")
    data = load_data()
    user_id = ctx.author.id
    ensure_account(data, user_id)
    if data[str(user_id)]["balance"] < amount:
        return await ctx.send("❌ رصيدك لا يكفي.")
    data[str(user_id)]["balance"] -= amount
    save_data(data)
    await ctx.send(f"✅ تم سحب {amount} نقطة من حسابك.")

@bot.command(name="تحويل")
async def transfer(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id:
        return await ctx.send("❌ لا يمكنك تحويل النقاط لنفسك.")
    if amount <= 0:
        return await ctx.send("❌ المبلغ يجب أن يكون أكبر من صفر.")
    data = load_data()
    sender_id = ctx.author.id
    receiver_id = member.id
    ensure_account(data, sender_id)
    ensure_account(data, receiver_id)
    if data[str(sender_id)]["balance"] < amount:
        return await ctx.send("❌ رصيدك لا يكفي للتحويل.")
    data[str(sender_id)]["balance"] -= amount
    data[str(receiver_id)]["balance"] += amount
    save_data(data)
    await ctx.send(f"✅ تم تحويل {amount} نقطة إلى {member.mention}.")

@bot.command(name="بنك")
async def bank_help(ctx):
    embed = discord.Embed(title="🏦 أوامر نظام البنك", color=0x00bfa5)
    embed.add_field(name="!رصيد", value="عرض رصيدك الحالي.", inline=False)
    embed.add_field(name="!ايداع [مبلغ]", value="إيداع مبلغ في حسابك.", inline=False)
    embed.add_field(name="!سحب [مبلغ]", value="سحب مبلغ من حسابك.", inline=False)
    embed.add_field(name="!تحويل [@مستخدم] [مبلغ]", value="تحويل مبلغ لشخص آخر.", inline=False)
    embed.add_field(name="!كم_ثروتك [@مستخدم] [مبلغ]", value="(للمالك فقط) إضافة مبلغ لرصيد أي شخص.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="كم_ثروتك")
async def add_balance(ctx, member: discord.Member, amount: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("❌ هذا الأمر خاص بالمالك فقط.")
    if amount <= 0:
        return await ctx.send("❌ المبلغ يجب أن يكون أكبر من صفر.")
    data = load_data()
    ensure_account(data, member.id)
    data[str(member.id)]["balance"] += amount
    save_data(data)
    await ctx.send(f"💸 تم إضافة {amount} نقطة إلى رصيد {member.mention} بنجاح.")
# ------------------ البوت يسولف -----------------------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')

@bot.command()
async def قول(ctx, *, النص):
    # تأكد ان المستخدم داخل روم صوتي
    if not ctx.author.voice:
        await ctx.send("لازم تكون داخل روم صوتي عشان أتكلم هناك!")
        return

    # إذا البوت مش داخل روم صوتي، يدخل روم المستخدم
    if not ctx.voice_client:
        channel = ctx.author.voice.channel
        await channel.connect()
    elif ctx.voice_client.channel != ctx.author.voice.channel:
        await ctx.voice_client.move_to(ctx.author.voice.channel)

    # تحويل النص لصوت وحفظه مؤقتًا
    tts = gTTS(text=النص, lang='ar')
    filename = "tts.mp3"
    tts.save(filename)

    voice_client = ctx.voice_client

    # تشغيل الصوت
    if not voice_client.is_playing():
        voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=filename))

        # انتظر حتى يخلص الصوت
        while voice_client.is_playing():
            await asyncio.sleep(1)

        # حذف الملف بعد ما يخلص
        os.remove(filename)
    else:
        await ctx.send("البوت يشغل صوت الآن، انتظر شوي!")
# ------------------- روليت ---------------------------

# رابط صورة GIF للروليت (غيره برابطك المباشر)
ROULETTE_GIF_URL = "https://cdn.discordapp.com/attachments/1385506924824625243/1385754577936191652/roulette_spin_fast_to_normal.gif?ex=68573805&is=6855e685&hm=3b24f7871e143a9af4e7c2e9b7104c2657410dcd15306dfd3c7f328be4bc6635&"

# خانات الروليت (تقدر تعدلها)
roulette_slots = [
    "💰 فلوس",
    "🍎 تفاحة",
    "🔥 نار",
    "🎁 صندوق مفاجأة",
    "💀 خسارة",
    "🎉 فوز كبير",
    "🧊 تجميد",
    "🌟 نجمة"
]

# كول داون 10 ثواني لكل مستخدم
@bot.command(name="Rolet")
@commands.cooldown(1, 10, commands.BucketType.user)
async def roulette(ctx):
    # إرسال GIF للروليت
    embed = discord.Embed(
        title="🎯 الروليت تدور...",
        description="⏳ انتظر النتيجة...",
        color=discord.Color.blurple()
    )
    embed.set_image(url=ROULETTE_GIF_URL)
    message = await ctx.send(embed=embed)

    # انتظر مدة الـGIF تقريباً 3 ثواني
    await asyncio.sleep(3.5)

    # اختيار خانة عشوائية
    result = random.choice(roulette_slots)

    # تحديث الرسالة بالنتيجة
    result_embed = discord.Embed(
        title="🎉 النتيجة!",
        description=f"**{ctx.author.mention}** حصل على: **{result}**",
        color=discord.Color.green()
    )
    result_embed.set_image(url=ROULETTE_GIF_URL)
    await message.edit(embed=result_embed)

# رسائل الخطأ عند تكرار الأمر قبل انتهاء الكول داون
@roulette.error
async def roulette_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ انتظر {round(error.retry_after, 1)} ثانية قبل استخدام الروليت مرة أخرى.", delete_after=5)

# ------------------- SoundCloud ---------------------
OWNER_ID = 948531215252742184
SONGS_FILE = "songs.json"

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

def load_songs():
    if os.path.exists(SONGS_FILE):
        try:
            with open(SONGS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_songs(songs):
    with open(SONGS_FILE, 'w') as f:
        json.dump(songs, f, indent=4)

saved_songs = load_songs()

def is_owner(ctx):
    return ctx.author.id == OWNER_ID

@bot.command()
@commands.check(is_owner)
async def join(ctx, channel_id: int):
    channel = bot.get_channel(channel_id)
    if isinstance(channel, discord.VoiceChannel):
        await channel.connect()
        await ctx.send(f"✅ انضممت إلى الروم الصوتي: {channel.name}")
    else:
        await ctx.send("❌ لم أتمكن من العثور على روم صوتي بهذا المعرف.")

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
    ffmpeg_opts = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_opts)
    player = discord.PCMVolumeTransformer(source, volume=1.0)
    voice_client.play(player)

    saved_songs["last_url"] = audio_url
    save_songs(saved_songs)

    duration = info.get("duration", 0)
    await ctx.send(f"🎵 جاري تشغيل: {info.get('title', 'مقطع صوتي')}\n⏱️ المدة: {int(duration // 60)}:{int(duration % 60):02d}")

    async def progress_bar():
        elapsed = 0
        message = await ctx.send(f"⏳ الوقت: 0:00 / {int(duration // 60)}:{int(duration % 60):02d}")
        while voice_client.is_playing() and elapsed < duration:
            await asyncio.sleep(5)
            elapsed += 5
            minutes = elapsed // 60
            seconds = elapsed % 60
            try:
                await message.edit(content=f"⏳ الوقت: {minutes}:{seconds:02d} / {int(duration // 60)}:{int(duration % 60):02d}")
            except discord.NotFound:
                break

    bot.loop.create_task(progress_bar())

@bot.command()
@commands.check(is_owner)
async def stop(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("⏹️ تم إيقاف التشغيل.")
    else:
        await ctx.send("❌ لا يوجد شيء يعمل حالياً.")

@bot.command()
@commands.check(is_owner)
async def name(ctx, url, name):
    saved_songs[name] = url
    save_songs(saved_songs)
    await ctx.send(f"✅ تم حفظ الأغنية باسم: {name}")

@bot.command()
@commands.check(is_owner)
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 تم الخروج من الروم الصوتي.")
    else:
        await ctx.send("❌ لست متصلاً بأي روم صوتي.")

@bot.command()
@commands.check(is_owner)
async def صوت(ctx, percentage: int):
    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_playing():
        await ctx.send("❌ لا يوجد شيء يعمل حالياً لتغيير صوته.")
        return

    source = voice_client.source
    if not isinstance(source, discord.PCMVolumeTransformer):
        await ctx.send("❌ لا يمكن تعديل الصوت لأن المصدر الحالي لا يدعم ضبط الصوت.")
        return

    if percentage < 1 or percentage > 100:
        await ctx.send("❌ الرجاء اختيار رقم بين 1 و 100 للصوت.")
        return

    volume = percentage / 100
    source.volume = volume
    await ctx.send(f"🔊 تم تعديل الصوت إلى {percentage}%")

@bot.command()
@commands.check(is_owner)
async def سرعه(ctx, speed: float):
    if speed <= 0:
        await ctx.send("❌ السرعة لازم تكون أكبر من 0.")
        return

    voice_client = ctx.guild.voice_client
    if not voice_client or not voice_client.is_playing():
        await ctx.send("❌ لا يوجد شيء يعمل حالياً لتعديل سرعته.")
        return

    current_url = saved_songs.get("last_url")
    if not current_url:
        await ctx.send("❌ لا يمكن تعديل السرعة حالياً.")
        return

    voice_client.stop()
    ffmpeg_opts = {
        'before_options': f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': f'-filter:a "atempo={speed}" -vn'
    }
    source = discord.FFmpegPCMAudio(current_url, **ffmpeg_opts)
    player = discord.PCMVolumeTransformer(source, volume=1.0)
    voice_client.play(player)

    await ctx.send(f"⚡ تم ضبط السرعة على {speed}x")

@bot.command()
@commands.check(is_owner)
async def وقت(ctx, time_str: str):
    voice_client = ctx.guild.voice_client
    if not voice_client:
        await ctx.send("❌ البوت غير متصل بصوت.")
        return

    current_url = saved_songs.get("last_url")
    if not current_url:
        await ctx.send("❌ لا يوجد مقطع لتقديمه.")
        return

    try:
        if ":" in time_str:
            minutes, seconds = map(int, time_str.split(":"))
            total_seconds = minutes * 60 + seconds
        else:
            total_seconds = int(time_str)
    except:
        await ctx.send("❌ صيغة الوقت غير صحيحة. استخدم: !وقت 1:30 أو !وقت 90")
        return

    voice_client.stop()
    ffmpeg_opts = {
        'before_options': f'-ss {total_seconds} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    source = discord.FFmpegPCMAudio(current_url, **ffmpeg_opts)
    player = discord.PCMVolumeTransformer(source, volume=1.0)
    voice_client.play(player)

    await ctx.send(f"⏩ تم الانتقال إلى الدقيقة: {total_seconds // 60}:{total_seconds % 60:02d}")

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
