import discord
from discord.ext import commands
from discord import app_commands
import json
import os
bot.run(os.getenv("MTM3NDgwNjY3MDAzNDczMTE5OA.Gs_ESL.F7KlV-zbzXnHbv62AClMluU8dbB0hjN2wgsEVM"))

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
TREE = bot.tree

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
    await TREE.sync()
    print(f"✅ Logged in as {bot.user}")

# /generate - يقوم بإنشاء رمز مربوط برتبة
@TREE.command(name="generate", description="إنشاء رمز مربوط برتبة")
@app_commands.describe(role="اختر الرتبة", code="أدخل الرمز اليدوي الذي تريده")
async def generate(interaction: discord.Interaction, role: discord.Role, code: str):
    codes = load_codes()
    
    if code in codes:
        await interaction.response.send_message("❌ هذا الرمز مستخدم من قبل.", ephemeral=True)
        return

    codes[code] = role.id
    save_codes(codes)
    await interaction.response.send_message(f"✅ تم إنشاء الرمز `{code}` للرتبة {role.mention}", ephemeral=True)

# /redeem - يستبدل الرمز برتبة
@TREE.command(name="redeem", description="استبدال رمز للحصول على رتبة")
@app_commands.describe(code="أدخل الرمز")
async def redeem(interaction: discord.Interaction, code: str):
    codes = load_codes()
    user = interaction.user

    if code not in codes:
        await interaction.response.send_message("❌ الرمز غير صحيح أو منتهي.", ephemeral=True)
        return

    role_id = codes[code]
    role = interaction.guild.get_role(role_id)

    if not role:
        await interaction.response.send_message("⚠️ الرتبة غير موجودة في السيرفر.", ephemeral=True)
        return

    await user.add_roles(role)
    del codes[code]
    save_codes(codes)

    await interaction.response.send_message(f"🎉 تم إعطاؤك الرتبة {role.mention} بنجاح!", ephemeral=False)
