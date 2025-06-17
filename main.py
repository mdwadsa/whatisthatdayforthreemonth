import discord
from discord.ext import commands
import json
import os

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

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

# !generate - يقوم بإنشاء رمز مربوط برتبة
@bot.command(name="generate")
@commands.has_permissions(administrator=True)  # مثلا صلاحيات الأدمن لتوليد الرمز
async def generate(ctx, role: discord.Role, code: str):
    codes = load_codes()

    if code in codes:
        await ctx.send("❌ هذا الرمز مستخدم من قبل.")
        return

    codes[code] = role.id
    save_codes(codes)
    await ctx.send(f"✅ تم إنشاء الرمز `{code}` للرتبة {role.mention}")

# !redeem - يستبدل الرمز برتبة
@bot.command(name="redeem")
async def redeem(ctx, code: str):
    codes = load_codes()
    user = ctx.author

    if code not in codes:
        await ctx.send("❌ الرمز غير صحيح أو منتهي.")
        return

    role_id = codes[code]
    role = ctx.guild.get_role(role_id)

    if not role:
        await ctx.send("⚠️ الرتبة غير موجودة في السيرفر.")
        return

    await user.add_roles(role)
    del codes[code]
    save_codes(codes)

    await ctx.send(f"🎉 تم إعطاؤك الرتبة {role.mention} بنجاح!")

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
