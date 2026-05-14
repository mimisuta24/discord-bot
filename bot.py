import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import json
import os
import time

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== 国データ =====
countries = {
    "japan": {
        "name": "日本",
        "aliases": ["japan", "日本", "にほん", "にっぽん"],
        "image": "https://cdn.discordapp.com/attachments/1501419834913587220/1501559919487484055/by_fune.png"
    },
    "usa": {
        "name": "アメリカ",
        "aliases": ["usa", "america", "アメリカ", "米国", "あめりか"],
        "image": "https://flagcdn.com/w320/us.png"
    },
    "france": {
        "name": "フランス",
        "aliases": ["france", "フランス", "ふらんす"],
        "image": "https://cdn.discordapp.com/attachments/1501412582412521675/1501412628482887822/by_saito.png"
    },
    "germany": {
        "name": "ドイツ",
        "aliases": ["germany", "ドイツ", "どいつ"],
        "image": "https://flagcdn.com/w320/de.png"
    },
    "china": {
        "name": "中国",
        "aliases": ["china", "ちゅうごく", "中国"],
        "image": "https://cdn.discordapp.com/attachments/1501419834913587220/1501569328343158836/China_by_yuito.png"
    }
}

# ===== データ保存 =====
if os.path.exists("collections.json"):
    with open("collections.json", "r", encoding="utf-8") as f:
        collections = json.load(f)
else:
    collections = {}

# ===== お金データ =====
if os.path.exists("money.json"):
    with open("money.json", "r", encoding="utf-8") as f:
        money = json.load(f)
else:
    money = {}

current_answer = None

# ===== メッセージ処理 =====
@bot.event
async def on_message(message):
    global current_answer

    if message.author.bot:
        return

    if current_answer:
        aliases = countries[current_answer]["aliases"]

        if message.content.strip().lower() in [a.lower() for a in aliases]:
            user = str(message.author)

            if user not in collections:
                collections[user] = []

            collections[user].append(current_answer)

            # コレクション保存
            with open("collections.json", "w", encoding="utf-8") as f:
                json.dump(collections, f, ensure_ascii=False, indent=4)

            # ===== お金処理 =====
            if user not in money:
                money[user] = 0

            reward = random.randint(10, 50)
            money[user] += reward

            with open("money.json", "w", encoding="utf-8") as f:
                json.dump(money, f, ensure_ascii=False, indent=4)

            await message.channel.send(
                f"{message.author.mention} 正解！ {countries[current_answer]['name']} をゲット！\n💰 +{reward}コイン"
            )

            current_answer = None
            daily_cooldown = {}

    await bot.process_commands(message)

# ===== 自動スポーン =====
@tasks.loop(seconds=600)
async def auto_spawn():
    global current_answer

    if current_answer is None:
        country = random.choice(list(countries.keys()))
        current_answer = country

        channel = bot.get_channel(1500806594458550302)

        if channel:
            await channel.send("🌍 国を当てて！")
            await channel.send(countries[country]["image"])

# ===== コレクション =====
@bot.tree.command(name="collection", description="コレクションを見る")
async def collection(interaction: discord.Interaction):
    user = str(interaction.user)

    if user not in collections or not collections[user]:
        embed = discord.Embed(
            title="📦 コレクション",
            description="まだ何も持っていません",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return

    from collections import Counter

    owned = collections[user]
    count = Counter(owned)

    lines = [f"{countries[k]['name']} ×{v}" for k, v in count.items()]

    embed = discord.Embed(
        title=f"📦 {interaction.user.name} のコレクション",
        description="\n".join(lines),
        color=discord.Color.blue()
    )

    all_countries = set(countries.keys())
    owned_set = set(owned)
    missing = all_countries - owned_set

    embed.add_field(
        name="📖 未所持",
        value=f"{len(missing)}種類",
        inline=False
    )

    if len(missing) == 0:
        embed.add_field(
            name="🎉 コンプリート！",
            value="すべての国を集めました！",
            inline=False
        )
        embed.color = discord.Color.gold()

    embed.set_footer(text=f"種類数: {len(count)} / 総数: {len(owned)}")

    await interaction.response.send_message(embed=embed)

# ===== ランキング =====
@bot.tree.command(name="ranking", description="ランキングを見る")
async def ranking(interaction: discord.Interaction):
    if not collections:
        await interaction.response.send_message("まだ誰も集めていません")
        return

    ranking_data = [(user, len(items)) for user, items in collections.items()]
    ranking_data.sort(key=lambda x: x[1], reverse=True)

    lines = []
    medals = ["🥇", "🥈", "🥉"]

    for i, (user, count) in enumerate(ranking_data[:10]):
        medal = medals[i] if i < 3 else f"{i+1}位"
        lines.append(f"{medal} {user} - {count}個")

    embed = discord.Embed(
        title="🏆 コレクションランキング",
        description="\n".join(lines),
        color=discord.Color.gold()
    )

    user_name = str(interaction.user)
    for i, (user, count) in enumerate(ranking_data):
        if user == user_name:
            embed.set_footer(text=f"あなたの順位: {i+1}位 ({count}個)")
            break

    await interaction.response.send_message(embed=embed)

# ===== 所持金 =====
@bot.tree.command(name="money", description="所持金を見る")
async def money_cmd(interaction: discord.Interaction):
    user = str(interaction.user)

    if user not in money:
        money[user] = 0

    embed = discord.Embed(
        title="💰 所持金",
        description=f"{interaction.user.mention} の残高: {money[user]}コイン",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)

# ===== デイリー =====
@bot.tree.command(name="daily", description="1日1回コインを受け取る")
async def daily(interaction: discord.Interaction):
    user = str(interaction.user)
    now = time.time()

    # 24時間チェック
    if user in daily_cooldown:
        remaining = 86400 - (now - daily_cooldown[user])

        if remaining > 0:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)

            await interaction.response.send_message(
                f"⏳ まだ受け取れません！\nあと {hours}時間 {minutes}分",
                ephemeral=True
            )
            return

    reward = random.randint(100, 300)

    if user not in money:
        money[user] = 0

    money[user] += reward
    daily_cooldown[user] = now

    with open("money.json", "w", encoding="utf-8") as f:
        json.dump(money, f, ensure_ascii=False, indent=4)

    embed = discord.Embed(
        title="🎁 デイリーボーナス",
        description=f"{reward}コイン獲得！",
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed)

# ===== 起動時 =====
@bot.event
async def on_ready():
    await bot.tree.sync()

    print(f"ログインしました: {bot.user}")

    auto_spawn.start()

# ===== 起動 =====
bot.run(os.getenv("TOKEN"))