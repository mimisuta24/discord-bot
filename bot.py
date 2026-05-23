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

            # プレイヤーデータ取得
            result = (
                supabase.table("players")
                .select("*")
                .eq("user_id", user)
                .execute()
            )

            data = result.data

            reward = random.randint(10, 50)

            # 初回プレイヤー
            if len(data) == 0:

                supabase.table("players").insert({
                    "user_id": user,
                    "coins": reward,
                    "countries": [current_answer]
                }).execute()

            else:

                player = data[0]

                countries_owned = player["countries"] or []
                countries_owned.append(current_answer)

                new_money = player["coins"] + reward

                supabase.table("players").update({
                    "coins": new_money,
                    "countries": countries_owned
                }).eq(
                    "user_id",
                    user
                ).execute()

            await message.channel.send(
                f"{message.author.mention} 正解！ "
                f"{countries[current_answer]['name']} をゲット！\n"
                f"💰 +{reward}コイン"
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

    result = (
        supabase.table("players")
        .select("countries")
        .eq("user_id", user)
        .execute()
    )

    if len(result.data) == 0:

        embed = discord.Embed(
            title="📦 コレクション",
            description="まだ何も持っていません",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)
        return

    owned = result.data[0]["countries"] or []

    if len(owned) == 0:

        embed = discord.Embed(
            title="📦 コレクション",
            description="まだ何も持っていません",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)
        return

    from collections import Counter

    count = Counter(owned)

    lines = []

    for country, amount in count.items():
        lines.append(
            f"{countries[country]['name']} ×{amount}"
        )

    embed = discord.Embed(
        title=f"📦 {interaction.user.name} のコレクション",
        description="\n".join(lines),
        color=discord.Color.blue()
    )

    missing = set(countries.keys()) - set(owned)

    embed.add_field(
        name="📖 未所持",
        value=f"{len(missing)}種類",
        inline=False
    )

    if len(missing) == 0:

        embed.add_field(
            name="🎉 コンプリート！",
            value="すべて集めました！",
            inline=False
        )

        embed.color = discord.Color.gold()

    embed.set_footer(
        text=f"種類数:{len(set(owned))} / 総数:{len(owned)}"
    )

    await interaction.response.send_message(embed=embed)

# ===== ランキング =====
@bot.tree.command(name="ranking", description="ランキングを見る")
async def ranking(interaction: discord.Interaction):

    result = (
        supabase.table("players")
        .select("*")
        .execute()
    )

    players = result.data

    if len(players) == 0:

        await interaction.response.send_message(
            "まだ誰も集めていません"
        )

        return

    ranking_data = []

    for player in players:

        count = len(player["countries"] or [])

        ranking_data.append(
            (player["user_id"], count)
        )

    ranking_data.sort(
        key=lambda x: x[1],
        reverse=True
    )

    medals = ["🥇", "🥈", "🥉"]
    lines = []

    for i, (user, count) in enumerate(ranking_data[:10]):

        medal = medals[i] if i < 3 else f"{i+1}位"

        lines.append(
            f"{medal} {user} - {count}個"
        )

    embed = discord.Embed(
        title="🏆 コレクションランキング",
        description="\n".join(lines),
        color=discord.Color.gold()
    )

    my_user = str(interaction.user)

    for i, (user, count) in enumerate(ranking_data):

        if user == my_user:

            embed.set_footer(
                text=f"あなたの順位: {i+1}位 ({count}個)"
            )

            break

    await interaction.response.send_message(embed=embed)

# ===== 所持金 =====
@bot.tree.command(name="money", description="所持金を見る")
async def money_cmd(interaction: discord.Interaction):

    user = str(interaction.user)

    result = (
        supabase.table("players")
        .select("coins")
        .eq("user_id", user)
        .execute()
    )

    coins = 0

    if len(result.data) > 0:
        coins = result.data[0]["coins"]

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
    now = int(time.time())

    result = (
        supabase.table("players")
        .select("*")
        .eq("user_id", user)
        .execute()
    )

    reward = random.randint(100, 300)

    # 初回
    if len(result.data) == 0:

        supabase.table("players").insert({
            "user_id": user,
            "coins": reward,
            "countries": [],
            "last_daily": now
        }).execute()

        await interaction.response.send_message(
            f"🎁 {reward}コイン獲得！"
        )

        return

    player = result.data[0]

    last_daily = player["last_daily"]

    if last_daily:

        remaining = 86400 - (now - last_daily)

        if remaining > 0:

            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)

            await interaction.response.send_message(
                f"⏳ あと {hours}時間 {minutes}分",
                ephemeral=True
            )

            return

    reward = random.randint(100, 300)

    new_money = player["coins"] + reward

    supabase.table("players").update({
        "coins": new_money,
        "last_daily": now
    }).eq(
        "user_id",
        user
    ).execute()

    await interaction.response.send_message(
        f"🎁 {reward}コイン獲得！"
    )

# ===== 起動時 =====
@bot.event
async def on_ready():

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game("国当てゲーム")
    )

    await bot.tree.sync()

    print(f"ログインしました: {bot.user}")

    auto_spawn.start()

# ===== 起動 =====
keep_alive()

bot.run(os.getenv("TOKEN"))