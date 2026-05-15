import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import os
import time
from supabase import create_client
from flask import Flask
from threading import Thread

# ===== Flask =====
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ===== Discord設定 =====
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== Supabase接続 =====
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

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

# ===== 変数 =====
current_answer = None
daily_cooldown = {}

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

            # ===== コレクション保存 =====
            cursor.execute(
                "INSERT INTO collections (user, country) VALUES (?, ?)",
                (user, current_answer)
            )

            conn.commit()

            # ===== お金処理 =====
            reward = random.randint(10, 50)

            cursor.execute(
                "SELECT coins FROM money WHERE user = ?",
                (user,)
            )

            result = cursor.fetchone()

            if result is None:
                cursor.execute(
                    "INSERT INTO money (user, coins) VALUES (?, ?)",
                    (user, reward)
                )
            else:
                new_money = result[0] + reward

                cursor.execute(
                    "UPDATE money SET coins = ? WHERE user = ?",
                    (new_money, user)
                )

            conn.commit()

            await message.channel.send(
                f"{message.author.mention} 正解！ {countries[current_answer]['name']} をゲット！\n💰 +{reward}コイン"
            )

            current_answer = None

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

    cursor.execute(
        "SELECT country FROM collections WHERE user = ?",
        (user,)
    )

    owned = [row[0] for row in cursor.fetchall()]

    if not owned:

        embed = discord.Embed(
            title="📦 コレクション",
            description="まだ何も持っていません",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)
        return

    from collections import Counter

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

    # コンプリート
    if len(missing) == 0:
        embed.add_field(
            name="🎉 コンプリート！",
            value="すべての国を集めました！",
            inline=False
        )

        embed.color = discord.Color.gold()

    embed.set_footer(
        text=f"種類数: {len(count)} / 総数: {len(owned)}"
    )

    await interaction.response.send_message(embed=embed)

# ===== ランキング =====
@bot.tree.command(name="ranking", description="ランキングを見る")
async def ranking(interaction: discord.Interaction):

    cursor.execute("""
    SELECT user, COUNT(*) as total
    FROM collections
    GROUP BY user
    ORDER BY total DESC
    """)

    ranking_data = cursor.fetchall()

    if not ranking_data:
        await interaction.response.send_message("まだ誰も集めていません")
        return

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
            embed.set_footer(
                text=f"あなたの順位: {i+1}位 ({count}個)"
            )

            break

    await interaction.response.send_message(embed=embed)

# ===== 所持金 =====
@bot.tree.command(name="money", description="所持金を見る")
async def money_cmd(interaction: discord.Interaction):

    user = str(interaction.user)

    cursor.execute(
        "SELECT coins FROM money WHERE user = ?",
        (user,)
    )

    result = cursor.fetchone()

    coins = result[0] if result else 0

    embed = discord.Embed(
        title="💰 所持金",
        description=f"{interaction.user.mention} の残高: {coins}コイン",
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed)

# ===== デイリー =====
@bot.tree.command(name="daily", description="1日1回コインを受け取る")
async def daily(interaction: discord.Interaction):

    user = str(interaction.user)
    now = time.time()

    # データ取得
    cursor.execute(
        "SELECT coins, last_daily FROM money WHERE user = ?",
        (user,)
    )

    result = cursor.fetchone()

    # 初回
    if result is None:

        reward = random.randint(100, 300)

        cursor.execute(
            "INSERT INTO money (user, coins, last_daily) VALUES (?, ?, ?)",
            (user, reward, now)
        )

        conn.commit()

        embed = discord.Embed(
            title="🎁 デイリーボーナス",
            description=f"{reward}コイン獲得！",
            color=discord.Color.gold()
        )

        await interaction.response.send_message(embed=embed)
        return

    coins, last_daily = result

    # 24時間チェック
    if last_daily is not None:

        remaining = 86400 - (now - last_daily)

        if remaining > 0:

            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)

            await interaction.response.send_message(
                f"⏳ まだ受け取れません！\nあと {hours}時間 {minutes}分",
                ephemeral=True
            )

            return

    # 報酬
    reward = random.randint(100, 300)
    new_coins = coins + reward

    cursor.execute(
        "UPDATE money SET coins = ?, last_daily = ? WHERE user = ?",
        (new_coins, now, user)
    )

    conn.commit()

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
keep_alive()

bot.run(os.getenv("TOKEN"))