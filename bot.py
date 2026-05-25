import discord
from discord.ui import Button, View, Modal, TextInput
from discord.ext import commands, tasks
import random
import os
import time
import asyncio

from supabase import create_client
from flask import Flask
from threading import Thread


# ===== Flask =====

app = Flask("")


@app.route("/")
def home():
    return "Bot is running!"


def run():
    app.run(host="0.0.0.0", port=10000)


def keep_alive():
    Thread(target=run).start()


# ===== Discord設定 =====

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ===== Supabase =====

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)


# ===== 国データ =====

countries = {

    "japan": {
        "name": "日本",
        "aliases": [
            "japan",
            "日本",
            "にほん",
            "にっぽん"
        ],
        "image":
        "https://cdn.discordapp.com/attachments/1501419834913587220/1501559919487484055/by_fune.png"
    },

    "usa": {
        "name": "アメリカ",
        "aliases": [
            "usa",
            "america",
            "アメリカ",
            "米国",
            "あめりか"
        ],
        "image":
        "https://cdn.discordapp.com/attachments/1501419834913587220/1507640185423401011/057bc90be89d4e6d.png"
    },

    "france": {
        "name": "フランス",
        "aliases": [
            "france",
            "フランス",
            "ふらんす"
        ],
        "image":
        "https://cdn.discordapp.com/attachments/1501412582412521675/1501412628482887822/by_saito.png"
    },

    "germany": {
        "name": "ドイツ",
        "aliases": [
            "germany",
            "ドイツ",
            "どいつ",
            "Federal Republic of Germany",
            "ドイツ連邦共和国"
        ],
        "image":
        "https://cdn.discordapp.com/attachments/1501419834913587220/1508073723163574343/by_cake.png"
    },

    "china": {
        "name": "中国",
        "aliases": [
            "china",
            "ちゅうごく",
            "中国",
            "中華人民共和国",
            "People's Republic of China"
        ],
        "image":
        "https://cdn.discordapp.com/attachments/1501419834913587220/1501569328343158836/China_by_yuito.png"
    },
    "south korea": {
        "name": "韓国",
        "aliases": [
            "korea",
            "north korea",
            "韓国",
            "大韓民国",
            "Republic of Korea",
            "かんこく",
            "南朝鮮"
        ],
        "image":
        "https://cdn.discordapp.com/attachments/1501419834913587220/1508444763614089378/bytank.png?ex=6a159029&is=6a143ea9&hm=e6de3834cfc4bacd451c52ab6900c566a1aaeba5d648f579ebd1543bb3360e8c&"
    },
    "russia": {
        "name": "ロシア",
        "aliases": [
            "ロシア",
            "russia",
            "ロシア連邦",
            "ろしあ",
            "Russian Federation"
        ],
        "image":
        "https://cdn.discordapp.com/attachments/1501419834913587220/1508445951944036503/by_.png?ex=6a159144&is=6a143fc4&hm=077f5f2515119c128a9363dfbd93c08dbd573d5980752774e10f24933e4686b7&"
    }

}


# ===== 状態 =====

current_answer = None
spawn_time = None
spawn_message = None

catch_lock = asyncio.Lock()


# ===== 国入力 =====

class CountryModal(Modal):

    def __init__(self):

        super().__init__(
            title="国名を入力"
        )

        self.country = TextInput(
            label="国名",
            placeholder="日本 / japan など"
        )

        self.add_item(
            self.country
        )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        global current_answer
        global spawn_time
        global spawn_message

        async with catch_lock:

            try:

                if current_answer is None:

                    await interaction.response.send_message(
                        "もう消えました",
                        ephemeral=True
                    )
                    return

                answer = (
                    self.country.value
                    .strip()
                    .lower()
                )

                aliases = [
                    a.lower()
                    for a in countries[
                        current_answer
                    ]["aliases"]
                ]

                if answer not in aliases:

                    await interaction.response.send_message(
                        "❌ 不正解",
                        ephemeral=True
                    )
                    return

                country = current_answer

                reward = random.randint(
                    10,
                    50
                )

                user = str(
                    interaction.user.id
                )

                result = (
                    supabase
                    .table("players")
                    .select("*")
                    .eq(
                        "user_id",
                        user
                    )
                    .execute()
                )

                if len(result.data) == 0:

                    supabase.table(
                        "players"
                    ).insert({

                        "user_id":
                        user,

                        "coins":
                        reward,

                        "countries":
                        [country]

                    }).execute()

                else:

                    player = result.data[0]

                    owned = (
                        player.get(
                            "countries"
                        )
                        or []
                    )

                    owned.append(
                        country
                    )

                    supabase.table(
                        "players"
                    ).update({

                        "coins":
                        player["coins"]
                        + reward,

                        "countries":
                        owned

                    }).eq(
                        "user_id",
                        user
                    ).execute()

                await interaction.response.send_message(

                    f"{interaction.user.mention} が正解！\n"
                    f"🌍 {countries[country]['name']} ゲット！\n"
                    f"💰 +{reward}コイン"

                )

                if spawn_message:

                    view = CatchView()

                    for child in view.children:
                        child.disabled = True

                    await spawn_message.edit(
                        view=view
                    )

                current_answer = None
                spawn_time = None
                spawn_message = None

            except Exception as e:

                print(
                    f"Modalエラー:{e}"
                )

# ===== ボタン =====

class CatchView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Catch the ball!",
        style=discord.ButtonStyle.primary
    )
    async def catch(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if current_answer is None:

            await interaction.response.send_message(
                "もう消えました",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            CountryModal()
        )


# ===== メッセージ処理 =====

@bot.event
async def on_message(message):

    global current_answer
    global spawn_time
    global spawn_message

    if message.author.bot:
        return

    if current_answer:

        async with catch_lock:

            if current_answer is None:

                await bot.process_commands(
                    message
                )
                return

            aliases = [

                a.lower()

                for a in countries[
                    current_answer
                ]["aliases"]

            ]

            answer = (
                message.content
                .strip()
                .lower()
            )

            if answer in aliases:

                country = current_answer

                reward = random.randint(
                    10,
                    50
                )

                user = str(
                    message.author.id
                )

                result = (

                    supabase
                    .table("players")
                    .select("*")
                    .eq(
                        "user_id",
                        user
                    )
                    .execute()

                )

                if len(result.data) == 0:

                    supabase.table(
                        "players"
                    ).insert({

                        "user_id":
                        user,

                        "coins":
                        reward,

                        "countries":
                        [country]

                    }).execute()

                else:

                    player = result.data[0]

                    owned = (
                        player.get(
                            "countries"
                        )
                        or []
                    )

                    owned.append(
                        country
                    )

                    supabase.table(
                        "players"
                    ).update({

                        "coins":
                        player["coins"]
                        + reward,

                        "countries":
                        owned

                    }).eq(
                        "user_id",
                        user
                    ).execute()

                await message.channel.send(

                    f"{message.author.mention} 正解！\n"
                    f"🌍 {countries[country]['name']} をゲット！\n"
                    f"💰 +{reward}コイン"

                )

                if spawn_message:

                    view = CatchView()

                    for child in view.children:
                        child.disabled = True

                    await spawn_message.edit(
                        view=view
                    )

                current_answer = None
                spawn_time = None
                spawn_message = None

    await bot.process_commands(
        message
    )


# ===== 自動スポーン =====

@tasks.loop(
    seconds=600
)
async def auto_spawn():

    global current_answer
    global spawn_time
    global spawn_message

    print(
        f"auto_spawn実行 "
        f"current_answer="
        f"{current_answer}"
    )

    try:

        now = time.time()

        if (

            current_answer
            is not None

            and

            spawn_time
            is not None

            and

            now - spawn_time
            >= 1200

        ):

            print(
                f"{current_answer}"
                " 時間切れ"
            )

            current_answer = None
            spawn_time = None

            if spawn_message:

                view = CatchView()

                for child in view.children:
                    child.disabled = True

                await spawn_message.edit(
                    view=view
                )

                spawn_message = None

        if current_answer is None:

            country = random.choice(
                list(
                    countries.keys()
                )
            )

            current_answer = country
            spawn_time = now

            channel = bot.get_channel(
                1500806594458550302
            )

            if channel:

                embed = discord.Embed(
                    title="🌍 国を当てて！",
                    color=discord.Color.blue()
                )

                embed.set_image(
                    url=countries[
                        country
                    ]["image"]
                )

                spawn_message = (
                    await channel.send(
                        embed=embed,
                        view=CatchView()
                    )
                )

                print(
                    f"{country}"
                    " を出現"
                )

    except Exception as e:

        print(
            f"auto_spawnエラー:"
            f"{e}"
        )


@auto_spawn.before_loop
async def before_auto_spawn():

    await bot.wait_until_ready()

    print(
        "auto_spawn準備完了"
    )

# ===== コレクション =====

@bot.tree.command(
    name="collection",
    description="コレクションを見る"
)
async def collection(
    interaction: discord.Interaction
):

    user = str(
        interaction.user.id
    )

    result = (
        supabase
        .table("players")
        .select("countries")
        .eq(
            "user_id",
            user
        )
        .execute()
    )

    owned = []

    if result.data:

        owned = (
            result.data[0]
            .get("countries")
            or []
        )

    if not owned:

        embed = discord.Embed(

            title="📦 コレクション",

            description=
            "まだ何も持っていません",

            color=
            discord.Color.red()

        )

        await interaction.response.send_message(
            embed=embed
        )
        return

    from collections import Counter

    count = Counter(
        owned
    )

    lines = []

    for country, amount in count.items():

        if country not in countries:
            continue

        lines.append(

            f"{countries[country]['name']}"
            f" ×{amount}"

        )

    embed = discord.Embed(

        title=
        f"📦 "
        f"{interaction.user.name}"
        f" のコレクション",

        description=
        "\n".join(lines),

        color=
        discord.Color.blue()

    )

    missing = (

        set(
            countries.keys()
        )

        -

        set(
            owned
        )

    )

    embed.add_field(

        name="📖 未所持",

        value=
        f"{len(missing)}種類",

        inline=False

    )

    if len(missing) == 0:

        embed.add_field(

            name="🎉 コンプリート！",

            value=
            "すべて集めました！",

            inline=False

        )

        embed.color = (
            discord.Color.gold()
        )

    embed.set_footer(

        text=
        f"種類数:"
        f"{len(set(owned))}"
        f" / 総数:"
        f"{len(owned)}"

    )

    await interaction.response.send_message(
        embed=embed
    )


# ===== ランキング =====
@bot.tree.command(
    name="ranking",
    description="ランキングを見る"
)
async def ranking(
    interaction: discord.Interaction
):

    try:

        await interaction.response.defer()

        result = (
            supabase
            .table("players")
            .select("*")
            .execute()
        )

        players = result.data

        if not players:

            await interaction.followup.send(
                "まだ誰も集めていません"
            )
            return

        ranking_data = []

        for player in players:

            owned = (
                player.get(
                    "countries",
                    []
                ) or []
            )

            count = len(owned)

            user_id = str(
                player.get(
                    "user_id",
                    "0"
                )
            )

            try:

                member = interaction.guild.get_member(
                    int(user_id)
                )

                if member:

                    name = member.display_name

                else:

                    user = await bot.fetch_user(
            int(user_id)
                    )

                    name = user.name

            except Exception as e:

                print(
                    f"壊れたデータ削除:"
                    f"{user_id}"
                )
            
                supabase.table(
                    "players"
                ).delete().eq(
                    "user_id",
                    user_id
                ).execute()

                continue

            ranking_data.append(
                (
                    name,
                    user_id,
                    count
                )
            )

        ranking_data.sort(
            key=lambda x:x[2],
            reverse=True
        )

        medals = [
            "🥇",
            "🥈",
            "🥉"
        ]

        lines = []

        for i,(
            name,
            uid,
            count
        ) in enumerate(
            ranking_data[:10]
        ):

            mark = (
                medals[i]
                if i < 3
                else f"{i+1}位"
            )

            lines.append(
                f"{mark} {name} {count}個"
            )

        embed = discord.Embed(
            title="🏆 コレクションランキング",
            description="\n".join(lines),
            color=discord.Color.gold()
        )

        my_id = str(
            interaction.user.id
        )

        for i,(
            _,
            uid,
            count
        ) in enumerate(
            ranking_data
        ):

            if uid == my_id:

                embed.set_footer(
                    text=
                    f"あなたの順位:"
                    f"{i+1}位 "
                    f"({count}個)"
                )

                break

        await interaction.followup.send(
            embed=embed
        )

    except Exception as e:

        print(
            f"rankingエラー:{e}"
        )

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "ランキング取得失敗",
                ephemeral=True
            )

        else:

            await interaction.followup.send(
                "ランキング取得失敗",
                ephemeral=True
            )

# ===== 所持金 =====

@bot.tree.command(
    name="money",
    description="所持金を見る"
)
async def money_cmd(
    interaction: discord.Interaction
):

    user = str(interaction.user.id)

    result = (
        supabase
        .table("players")
        .select("coins")
        .eq(
            "user_id",
            user
        )
        .execute()
    )

    coins = 0

    if result.data:
        coins = (
            result.data[0]
            .get("coins", 0)
        )

    embed = discord.Embed(
        title="💰 所持金",
        description=(
            f"{interaction.user.name}"
            f" の所持金: {coins}コイン"
        ),
        color=discord.Color.green()
    )

    await interaction.response.send_message(
        embed=embed
    )

# ===== デイリー =====

@bot.tree.command(
    name="daily",
    description=
    "1日1回コインを受け取る"
)
async def daily(
    interaction:
    discord.Interaction
):

    user = str(
        interaction.user.id
    )

    now = int(
        time.time()
    )

    result = (

        supabase
        .table("players")
        .select("*")
        .eq(
            "user_id",
            user
        )
        .execute()

    )

    reward = random.randint(
        100,
        300
    )

    if not result.data:

        supabase.table(
            "players"
        ).insert({

            "user_id":
            user,

            "coins":
            reward,

            "countries":
            [],

            "last_daily":
            now

        }).execute()

        await interaction.response.send_message(

            f"🎁 "
            f"{reward}"
            f"コイン獲得！"

        )

        return

    player = result.data[0]

    last = player.get(
        "last_daily"
    )

    if last:

        remain = (

            86400
            -
            (now-last)

        )

        if remain > 0:

            h = remain // 3600
            m = (

                remain % 3600

            ) // 60

            await interaction.response.send_message(

                f"⏳ "
                f"{h}時間"
                f"{m}分"

            )

            return

    money = (

        player["coins"]

        +

        reward

    )

    supabase.table(
        "players"
    ).update({

        "coins":
        money,

        "last_daily":
        now

    }).eq(

        "user_id",

        user

    ).execute()

    await interaction.response.send_message(

        f"🎁 "
        f"{reward}"
        f"コイン獲得！"

    )


# ===== 起動 =====

@bot.event
async def on_ready():

    print(
        "起動完了"
    )

    await bot.change_presence(

        activity=
        discord.Game(
            "国当てゲーム"
        )

    )

    await bot.tree.sync()

    if not auto_spawn.is_running():

        auto_spawn.start()

        print(
            "auto_spawn開始"
        )

    print(

        f"ログイン:"
        f"{bot.user}"

    )


keep_alive()

print(
    "起動開始"
)

bot.run(
    os.getenv(
        "TOKEN"
    )
)