import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import urllib.parse, urllib.request, re

def run():
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix="!", intents=intents)

    # Lista de comandos para o autocomplete
    COMMAND_LIST = ["play", "stop", "pause", "resume", 
                    "queue", "clear_queue", "skip", "help-me"]

    queues = {}
    voice_clients = {}
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.5"'}

    # Comando com dropdown (autocomplete)
    @client.tree.command(name="comando", description="Comando com suporte a autocomplete")
    async def comando(interaction: discord.Interaction, option: str):
        await interaction.response.send_message(f"Escolheste: {option}", ephemeral=True)

    # Função de autocomplete para o comando
    @comando.autocomplete("option")
    async def autocomplete_option(interaction: discord.Interaction, current: str):
        # Filtra a lista de comandos com base no que o utilizador digitou
        suggestions = [cmd for cmd in COMMAND_LIST if current.lower() in cmd.lower()]
        # Retorna até 25 opções (limite da API do Discord)
        return [app_commands.Choice(name=cmd, value=cmd) for cmd in suggestions[:25]]


    @client.event
    async def on_ready():
        print(f'{client.user} is now jamming')

    async def play_next(ctx):
        if queues[ctx.guild.id]:  # Verifica se há músicas na fila
            link = queues[ctx.guild.id].pop(0)
            await play(ctx, link=link)
        else:
            # Se a fila estiver vazia, desconecta o bot
            await ctx.guild.voice_client.disconnect()
            del voice_clients[ctx.guild.id]
            await ctx.send("Não há mais músicas na fila. Desconectando...")

                
    @client.command(name="play")
    async def play(ctx, *, link):
        try:
            # Verifica se já há uma música tocando no servidor
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
                # Se já houver música tocando, adiciona à fila
                if ctx.guild.id not in queues:
                    queues[ctx.guild.id] = []
                queues[ctx.guild.id].append(link)
                await ctx.send(f"```Adicionada à fila:``` {link}")
                return
            
            # Caso não haja música tocando, conecta ao canal de voz
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            print(e)

        try:
            # Se o link não for uma URL do YouTube, faz uma pesquisa
            if youtube_base_url not in link:
                await ctx.send(f"```Searching the top matches for: {link}```")  # Feedback ao usuário sobre a pesquisa
                query_string = urllib.parse.urlencode({'search_query': link})
                content = urllib.request.urlopen(youtube_results_url + query_string)
                search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                link = youtube_watch_url + search_results[0]  # Pega o primeiro resultado
                await ctx.send(f"Now playing: {link}")  # Feedback com o link do vídeo que será tocado

            # Extrai o URL do áudio com yt-dlp
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            song = data['url']
            player = discord.FFmpegOpusAudio(song, **ffmpeg_options)

            # Reproduz a música imediatamente
            voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
        except Exception as e:
            print(e)

    @client.command(name="clear_queue")
    async def clear_queue(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("```Queue cleared!```")
        else:
            await ctx.send("```There is no queue to clear```")

    @client.command(name="pause")
    async def pause(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(e)

    @client.command(name="resume")
    async def resume(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(e)

    @client.command(name="stop")
    async def stop(ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
        except Exception as e:
            print(e)

    @client.command(name="queue")
    async def queue(ctx):
        # Verifica se o servidor já tem uma fila
        if ctx.guild.id in queues and len(queues[ctx.guild.id]) > 0:
            # Exibe as músicas na fila
            queue_list = "\n".join(queues[ctx.guild.id])
            await ctx.send(f"```Fila de músicas:\n{queue_list}```")
        else:
            await ctx.send("```A fila está vazia.```")


    @client.command(name="skip")
    async def skip(ctx):
        try:
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
                voice_clients[ctx.guild.id].stop()  # Para a música atual
                await ctx.send("```Skipping to the next track...```")
                await play_next(ctx)  # Chama a função para tocar a próxima música
            else:
                await ctx.send("No music is currently playing!")
        except Exception as e:
            print(e)

    @client.command(name="help-me")
    async def help(ctx):

        help_message = """
            **🎵 Comandos disponíveis:**

            **1. `!play <link>`** ➡️ Reproduz a música do link que enviaste.
            **2. `!pause`** ➡️ Dá uma pausa à música. Calma, respira!
            **3. `!resume`** ➡️ Retoma a música. Bora lá!
            **4. `!stop`** ➡️ Para tudo. Já queres acabar com a festa?
            **5. `!skip`** ➡️ Salta esta música. Próxima, por favor!
            **6. `!queue`** ➡️ Mostra a fila atual. O que vem a seguir, Zé?
            **7. `!clear_queue`** ➡️ Limpa a fila de músicas. Vamos recomeçar! 🎶
        """

        await ctx.send(help_message)


    client.run(TOKEN)