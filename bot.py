import discord
from discord.ext import commands
from pytube import YouTube
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Inicializar o bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

queue = []

async def play_music(ctx, url):
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send("Você precisa estar em um canal de voz para usar este comando.")
        return

    # Conectar ao canal de voz
    if not ctx.voice_client:
        voice_client = await voice_channel.connect()
    else:
        voice_client = ctx.voice_client

    # Usando o Pytube para pegar o áudio do vídeo
    yt = YouTube(url)
    audio_stream = yt.streams.filter(only_audio=True).first()

    # Caminho para salvar o arquivo de áudio temporário
    audio_file = f"{yt.title}.mp4"
    audio_stream.download(filename=audio_file)

    # Usando FFmpeg para reproduzir o áudio no Discord
    audio_source = discord.FFmpegPCMAudio(audio_file, **ffmpeg_options)
    
    # Se já está tocando, adiciona à fila, senão começa a tocar
    if voice_client.is_playing():
        queue.append(audio_source)
        await ctx.send(f"Música adicionada à fila: {yt.title}")
    else:
        voice_client.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(after_play(ctx), bot.loop))
        await ctx.send(f"Tocando agora: {yt.title}")

async def after_play(ctx):
    if queue:
        next_song = queue.pop(0)
        voice_client = ctx.voice_client
        voice_client.play(next_song, after=lambda e: asyncio.run_coroutine_threadsafe(after_play(ctx), bot.loop))

@bot.command(name='play')
async def play(ctx, url):
    if url:
        await play_music(ctx, url)
    else:
        await ctx.send("Por favor, forneça um link de música.")

@bot.command(name='pause')
async def pause(ctx):
    if ctx.voice_client:
        ctx.voice_client.pause()
        await ctx.send("Música pausada.")
    else:
        await ctx.send("Não há música tocando no momento.")

@bot.command(name='resume')
async def resume(ctx):
    if ctx.voice_client:
        ctx.voice_client.resume()
        await ctx.send("Música retomada.")
    else:
        await ctx.send("Não há música tocando no momento.")

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Música parada e desconectado do canal.")
    else:
        await ctx.send("Não estou tocando música.")

@bot.command(name='queue')
async def queue(ctx):
    if queue:
        queue_list = '\n'.join([str(i) for i in queue])
        await ctx.send(f"Fila de músicas:\n{queue_list}")
    else:
        await ctx.send("Não há músicas na fila.")

@bot.command(name='help-menu')
async def help_command(ctx):
    help_text = """
    **Comandos do Bot de Música**:
    - `/play [url]` - Toca música ou vídeo.
    - `/pause` - Pausa a música.
    - `/resume` - Retoma a música.
    - `/stop` - Para a música e desconecta.
    - `/queue` - Exibe a fila de músicas.
    """
    await ctx.send(help_text)

# Rodar o bot
bot.run(TOKEN)
