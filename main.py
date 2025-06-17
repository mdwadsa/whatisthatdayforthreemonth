import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from aiohttp import web

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.presences = True  # ضروري لمراقبة الحالة

bot = commands.Bot(command_prefix="!", intents=intents)

# ملف لتخزين الرموز
CODES_FILE = "codes.json"

def load_codes():
    if not os.path.exists(CODES_FILE):
        return {}
    with open(CODES_FILE, "r") as f:
        return json.load(f)

def save_codes(codes):
    with open(CODES_FILE, "w") as f:
        json.dump(codes, f, indent=4)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    online_ping_task.start()

# !generate - يقوم بإنشاء رمز مربوط برتبة
@bot.command(name="generate")
@commands.has_permissions(administrator=True)
async def generate(ctx, role: discord.Role, code: str):
    codes = load_codes()
    if code in codes:
        await ctx.send("❌ هذا الرمز مستخدم من قبل.")
        return
    codes[code] = role.id
    save_codes(codes)
    await ctx.send(f"✅ تم إنشاء الرمز `{code}` للرتبة {role.mention}")

# !redeem - يستبدل الرمز برتبة + يدعم منشن
@bot.command(name="redeem")
async def redeem(ctx, target: discord.Member, code: str = None):
    if code is None:
        # في حالة ما حط المستخدم الرمز بعد المنشن (مثلاً: !redeem @user الرمز)
        await ctx.send("❌ الرجاء كتابة الرمز بعد المنشن. مثال: `!redeem @user الرمز`")
        return

    codes = load_codes()

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
    save_codes(codes)

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
                # إذا العضو مش بالسيرفر، نشيل من المتابعة
                online_watchlist.pop(user_id)
                continue
            current_status = member.status
            last_status = online_watchlist.get(user_id)
            if current_status != last_status:
                online_watchlist[user_id] = current_status
                owner = guild.owner  # ترسل لصاحب السيرفر (تقدر تغير لمنشنك انت أو غيره)
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
    # شغل الويب سيرفر مع البوت بنفس الوقت
    await run_webserver()
    await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

asyncio.run(main())
