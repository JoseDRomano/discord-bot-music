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
                    "queue", "clear", "skip", "help-me"]

    queues = {}
    voice_clients = {}
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.5"'}

    @client.event
    async def on_ready():
        print(f'{client.user} is now jamming')
        try:
            synced = await client.tree.sync()
            print(f"Synced {len(synced)} commands")
        except Exception as e:
            print(e)

    async def play_next(ctx):
        if queues.get(ctx.guild.id):  # Verifica se há músicas na fila
            next_song = queues[ctx.guild.id].pop(0)
            await play_audio(ctx, next_song)
        else:
            await ctx.send("✅ Fila vazia! Adiciona mais músicas para continuar.")

    async def play_audio(ctx, link):
        try:
            # Configurações otimizadas para playlists
            ytdl_options = {
                'format': 'bestaudio/best',
                'extract_flat': True,  # Modo eficiente para playlists
                'playlistend': 15,     # Limite máximo de músicas
                'quiet': True
            }
            ytdl = yt_dlp.YoutubeDL(ytdl_options)

            data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            if 'entries' in data:  # É uma playlist
                # Filtra apenas entradas válidas e limita a 45 músicas
                valid_entries = [entry for entry in data['entries'] if entry.get('id')][:45]
                
                if not valid_entries:
                    await ctx.send("⚠️ Não foi possível encontrar músicas válidas nesta playlist!")
                    return

                # Processa a primeira música imediatamente
                first_video = valid_entries[0]
                first_video_url = youtube_watch_url + first_video['id']
                
                # Extrai detalhes apenas da primeira música
                first_video_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: ytdl.extract_info(first_video_url, download=False))
                
                song = first_video_data['url']
                player = discord.FFmpegOpusAudio(song, **ffmpeg_options)
                
                voice_clients[ctx.guild.id].play(player, 
                    after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
                await ctx.send(f"▶️ Tocando agora: {first_video_data.get('title', 'Música desconhecida')}")

                # Adiciona as demais músicas (máximo 29 pois já tocamos a primeira)
                added_count = 0
                for entry in valid_entries[1:45]:  # Limite de 45 no total
                    if ctx.guild.id not in queues:
                        queues[ctx.guild.id] = []
                    
                    video_url = youtube_watch_url + entry['id']
                    queues[ctx.guild.id].append(video_url)
                    added_count += 1
                    await ctx.send(f"📝 Adicionada à fila: {entry.get('title', 'Música desconhecida')}")

                await ctx.send(f"✅ Playlist adicionada! Total de músicas: {added_count + 1}")
                return

            # Processamento normal para vídeos individuais
            song = data['url']
            player = discord.FFmpegOpusAudio(song, **ffmpeg_options)
            voice_clients[ctx.guild.id].play(player, 
                after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))
            await ctx.send(f"▶️ Tocando agora: {data.get('title', 'Música desconhecida')}")

        except Exception as e:
            print(f"Erro: {e}")
            await ctx.send("⚠️ Ocorreu um erro ao processar a música/playlist")

    @client.command(name="play")
    async def play(ctx, *, query):
        try:
            # Verifica se o usuário está em um canal de voz
            if not ctx.author.voice:
                await ctx.send("Você precisa estar em um canal de voz para usar este comando!")
                return

            # Conecta ao canal de voz se não estiver conectado
            if ctx.guild.id not in voice_clients:
                voice_client = await ctx.author.voice.channel.connect()
                voice_clients[ctx.guild.id] = voice_client
            elif not voice_clients[ctx.guild.id].is_connected():
                await voice_clients[ctx.guild.id].move_to(ctx.author.voice.channel)

            # Se já houver música tocando, adiciona à fila
            if voice_clients[ctx.guild.id].is_playing() or voice_clients[ctx.guild.id].is_paused():
                if youtube_base_url in query:  # É um link do YouTube
                    if "list=" in query:  # É uma playlist
                        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
                        for entry in data['entries']:
                            if ctx.guild.id not in queues:
                                queues[ctx.guild.id] = []
                            queues[ctx.guild.id].append(entry['webpage_url'])
                            await ctx.send(f"Adicionada à fila: {entry['title']}")
                    else:  # É um vídeo único
                        if ctx.guild.id not in queues:
                            queues[ctx.guild.id] = []
                        queues[ctx.guild.id].append(query)
                        data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
                        await ctx.send(f"Adicionada à fila: {data['title']}")
                else:  # É uma pesquisa
                    query_string = urllib.parse.urlencode({'search_query': query})
                    content = urllib.request.urlopen(youtube_results_url + query_string)
                    search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                    link = youtube_watch_url + search_results[0]
                    
                    if ctx.guild.id not in queues:
                        queues[ctx.guild.id] = []
                    queues[ctx.guild.id].append(link)
                    
                    data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
                    await ctx.send(f"Adicionada à fila: {data['title']}")
                return
            
            # Se não estiver tocando nada, começa a tocar imediatamente
            if youtube_base_url in query:  # É um link do YouTube
                await play_audio(ctx, query)
            else:  # É uma pesquisa
                query_string = urllib.parse.urlencode({'search_query': query})
                content = urllib.request.urlopen(youtube_results_url + query_string)
                search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                link = youtube_watch_url + search_results[0]
                await play_audio(ctx, link)

        except Exception as e:
            print(e)
            await ctx.send("Ocorreu um erro ao processar seu pedido.")

    @client.command(name="clear", aliases=["clear_queue"])
    async def clear_queue(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Fila limpa com sucesso!")
        else:
            await ctx.send("Não há fila para limpar!")

    @client.command(name="pause")
    async def pause(ctx):
        try:
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
                voice_clients[ctx.guild.id].pause()
                await ctx.send("Música pausada.")
            else:
                await ctx.send("Nenhuma música está tocando no momento.")
        except Exception as e:
            print(e)

    @client.command(name="resume")
    async def resume(ctx):
        try:
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_paused():
                voice_clients[ctx.guild.id].resume()
                await ctx.send("Música retomada.")
            else:
                await ctx.send("Nenhuma música está pausada no momento.")
        except Exception as e:
            print(e)

    @client.command(name="stop")
    async def stop(ctx):
        try:
            if ctx.guild.id in voice_clients:
                if ctx.guild.id in queues:
                    queues[ctx.guild.id].clear()
                voice_clients[ctx.guild.id].stop()
                await voice_clients[ctx.guild.id].disconnect()
                del voice_clients[ctx.guild.id]
                await ctx.send("Desconectado do canal de voz.")
        except Exception as e:
            print(e)

    @client.command(name="queue")
    async def queue(ctx):
        if ctx.guild.id in queues and len(queues[ctx.guild.id]) > 0:
            queue_list = []
            for i, link in enumerate(queues[ctx.guild.id], 1):
                try:
                    data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
                    title = data.get('title', link)
                    queue_list.append(f"{i}. {title}")
                except:
                    queue_list.append(f"{i}. {link}")
            
            message = "Fila de músicas:\n" + "\n".join(queue_list)
            if len(message) > 2000:
                message = message[:1997] + "..."
            await ctx.send(f"```{message}```")
        else:
            await ctx.send("A fila está vazia!")

    @client.command(name="skip")
    async def skip(ctx):
        try:
            if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
                voice_clients[ctx.guild.id].stop()
                await ctx.send("Pulando para a próxima música...")
                # play_next será chamado automaticamente pelo callback after
            else:
                await ctx.send("Nenhuma música está tocando no momento.")
        except Exception as e:
            print(e)

    @client.command(name="help-me")
    async def help(ctx):
        help_message = """
        **🎵 Comandos disponíveis:**

        **1. `!play <nome/link>`** ➡️ Reproduz a música ou adiciona à fila. Aceita nomes, links de vídeos ou playlists do YouTube.
        **2. `!pause`** ➡️ Pausa a música atual.
        **3. `!resume`** ➡️ Retoma a música pausada.
        **4. `!stop`** ➡️ Para a música e desconecta o bot.
        **5. `!skip`** ➡️ Pula para a próxima música na fila.
        **6. `!queue`** ➡️ Mostra a fila de músicas.
        **7. `!clear`** ➡️ Limpa a fila de músicas.
        """
        await ctx.send(help_message)

    client.run(TOKEN)
