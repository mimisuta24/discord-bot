import discord
from discord.ui import Button, View, Modal, TextInput
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
        "image": "https://cdn.discordapp.com/attachments/1501419834913587220/1507640185423401011/057bc90be89d4e6d.png?ex=6a12a2d6&is=6a115156&hm=0070bb2f98bbbf48efe4ff83111782bef699772da258cbafdc7b30caa18d551a&"
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
        "aliases": ["china", "ちゅうごく", "中国", "中華人民共和国", "People's Republic of China"],
        "image": "https://cdn.discordapp.com/attachments/1501419834913587220/1501569328343158836/China_by_yuito.png"
    }
}

# ===== 変数 =====
current_answer = None
spawn_time = None
spawn_message = None
daily_cooldown = {}

# ===== 国入力ポップ =====
class CountryModal(Modal):

    def __init__(self):
        super().__init__(title="国名を入力")

        self.country = TextInput(
            label="国名",
            placeholder="日本 / japan など"
        )

        self.add_item(self.country)

async def on_submit(
    self,
    interaction: discord.Interaction
):

    global current_answer
    global spawn_time
    global spawn_message

    try:

        if current_answer is None:

            await interaction.response.send_message(
                "もう消えました",
                ephemeral=True
            )
            return

        aliases = countries[
            current_answer
        ]["aliases"]

        answer = self.country.value.lower()

        if answer not in [
            a.lower()
            for a in aliases
        ]:

            await interaction.response.send_message(
                "❌ 不正解",
                ephemeral=True
            )
            return

        reward=random.randint(10,50)

        await interaction.response.send_message(
            "✅ 正解！"
        )

        if spawn_message:

            view=CatchView()

            for child in view.children:
                child.disabled=True

            await spawn_message.edit(
                view=view
            )

        current_answer=None
        spawn_time=None
        spawn_message=None

    except Exception as e:

        print(
            f"Modalエラー: {e}"
        )

# ===== ボタン =====
class CatchView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Catch the ball!",
        style=discord.ButtonStyle.primary
    )
    async def catch(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        await interaction.response.send_modal(
            CountryModal()
        )

# ===== メッセージ処理 =====
@bot.event
async def on_message(message):
    global current_answer
    global spawn_time

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
            spawn_time = None

    await bot.process_commands(message)

# ===== 自動スポーン =====
@tasks.loop(seconds=600)
async def auto_spawn():
    global current_answer
    global spawn_time

    print(
        f"auto_spawn実行 current_answer={current_answer}"
    )

    try:

        now = time.time()

        # 20分経過したら消す
        if (
            current_answer is not None
            and spawn_time is not None
            and now - spawn_time >= 1200
        ):

            print(
                f"{current_answer} 時間切れ"
            )

            current_answer = None
            spawn_time = None

        # 新しい国出現
        if current_answer is None:

            country = random.choice(
                list(countries.keys())
            )

            current_answer = country
            spawn_time = now

            channel = bot.get_channel(
                1500806594458550302
            )

            if channel:

                embed = discord.Embed(
                title="🌍 国を当てて！"
                )

                embed.set_image(
                url=countries[country]["image"]
                )

                global spawn_message

                spawn_message = await channel.send(
                    embed=embed,
                    view=CatchView()
                )

                print(
                    f"{country} を出現"
                )

    except Exception as e:

        print(
            f"auto_spawnエラー: {e}"
        )


@auto_spawn.before_loop
async def before_auto_spawn():

    await bot.wait_until_ready()

    print("auto_spawn準備完了")

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

# ===== 即時スポーン =====
@bot.tree.command(
    name="spawn",
    description="100コインで国を即時出現"
)
async def spawn_cmd(
    interaction: discord.Interaction
):

    global current_answer
    global spawn_time

    user = str(interaction.user)

    result = (
        supabase.table("players")
        .select("*")
        .eq("user_id", user)
        .execute()
    )

    if len(result.data) == 0:

        await interaction.response.send_message(
            "100コイン必要です",
            ephemeral=True
        )
        return

    player = result.data[0]
    coins = player["coins"]

    if coins < 100:

        await interaction.response.send_message(
            "💰 コイン不足です（100必要）",
            ephemeral=True
        )
        return

    if current_answer is not None:

        await interaction.response.send_message(
            "🌍 まだ未回答の国があります",
            ephemeral=True
        )
        return

    new_money = coins - 100

    supabase.table("players").update({
        "coins": new_money
    }).eq(
        "user_id",
        user
    ).execute()

    country = random.choice(
        list(countries.keys())
    )

    current_answer = country
    spawn_time = time.time()

    channel = bot.get_channel(
        1500806594458550302
    )

    if channel:

        await channel.send(
            f"⚡ {interaction.user.mention} が100コインで即時スポーン！"
        )

        embed = discord.Embed(
            title="🌍 国を当てて！"
        )

        embed.set_image(
            url=countries[country]["image"]
        )

        global spawn_message

        spawn_message = await channel.send(
            embed=embed,
            view=CatchView()
        )

    await interaction.response.send_message(
        "100コイン消費しました",
        ephemeral=True
    )

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

    # 報酬
    reward = random.randint(100, 300)
    new_money = player["coins"] + reward

    supabase.table("players").update({
        "coins": new_money,
        "last_daily": int(now)
    }).eq(
        "user_id",
        user
    ).execute()

    embed = discord.Embed(
        title="🎁 デイリーボーナス",
        description=f"{reward}コイン獲得！",
        color=discord.Color.gold()
    )

    await interaction.response.send_message(
        embed=embed
    )

# ===== 起動時 =====
@bot.event
async def on_ready():

    print("on_ready開始")

    try:

        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game("国当てゲーム")
        )

        print("プレゼンス設定完了")

        await bot.tree.sync()

        print("コマンド同期完了")

        print(
            f"ログインしました: {bot.user}"
        )

        print(
            f"auto_spawn動作中:{auto_spawn.is_running()}"
        )

        if not auto_spawn.is_running():

            auto_spawn.start()

            print(
                "auto_spawn開始"
            )

    except Exception as e:

        print(
            f"on_readyエラー:{e}"
        )

# ===== 起動 =====

keep_alive()

print("bot.run直前")

bot.run(os.getenv("TOKEN"))