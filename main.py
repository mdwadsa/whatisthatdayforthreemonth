import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from aiohttp import web
from datetime import datetime

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.presences = True  # ضروري لمراقبة الحالة

bot = commands.Bot(command_prefix="!", intents=intents)

# ملف لتخزين الرموز
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

# !generate - يقوم بإنشاء رمز مربوط برتبة
@bot.command(name="generate")
@commands.has_permissions(administrator=True)
async def generate(ctx, role: discord.Role, code: str):
    codes = load_json(CODES_FILE)
    if code in codes:
        await ctx.send("❌ هذا الرمز مستخدم من قبل.")
        return
    codes[code] = role.id
    save_json(CODES_FILE, codes)
    await ctx.send(f"✅ تم إنشاء الرمز `{code}` للرتبة {role.mention}")

# !redeem - يستبدل الرمز برتبة + يدعم منشن
@bot.command(name="redeem")
async def redeem(ctx, target: discord.Member, code: str = None):
    if code is None:
        await ctx.send("❌ الرجاء كتابة الرمز بعد المنشن. مثال: `!redeem @user الرمز`")
        return

    codes = load_json(CODES_FILE)

    if code not in codes:
        await ctx.send("❌ الرمز غير صحيح أو منتهي.")
        return

    role_id = codes[code]
    role = ctx.guild.get_role(role_id)

    if not role:
        await ctx.send("⚠️ الرتبة غير موجودة في السيرفر.")
        return

    await target.add_roles(role)
    del codes[code]
    save_json(CODES_FILE, codes)

    await ctx.send(f"🎉 تم إعطاء الرتبة {role.mention} للعضو {target.mention} بنجاح!")

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
        description=f"📅 آخر تسجيل دخول: {login_time}\n🕒 مدة تسجيل الدخول: {delta}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# ----------- تشغيل ويب سيرفر بسيط للحفاظ على البوت حي -----------

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
