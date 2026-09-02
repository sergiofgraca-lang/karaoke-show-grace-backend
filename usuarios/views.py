import json
import os
import re
import unicodedata

import yt_dlp

from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Musica


# =========================================================
# LIMPAR TEXTO
# =========================================================

def limpar_texto(texto):
    """Remove caracteres especiais e normaliza strings."""

    if not texto:
        return "Desconhecido"

    texto = (
        unicodedata.normalize("NFKD", str(texto))
        .encode("ascii", "ignore")
        .decode("utf-8")
    )

    return texto.strip()


# =========================================================
# PROCESSAR ÁUDIO DO YOUTUBE
# =========================================================

@csrf_exempt
def processar_audio_youtube(request):

    # -----------------------------------------------------
    # 1. VALIDAR MÉTODO
    # -----------------------------------------------------

    if request.method != "POST":
        return JsonResponse(
            {
                "erro": "Método inválido. Use POST."
            },
            status=405
        )

    # -----------------------------------------------------
    # 2. CAPTURAR DADOS
    # -----------------------------------------------------

    if request.content_type == "application/json":

        try:
            dados = json.loads(request.body)

            video_id = dados.get("videoId")
            titulo = dados.get("titulo")
            cantor = dados.get("cantor", "")

        except json.JSONDecodeError:

            return JsonResponse(
                {
                    "erro": "JSON inválido."
                },
                status=400
            )

    else:

        video_id = request.POST.get("videoId")
        titulo = request.POST.get("titulo")
        cantor = request.POST.get("cantor", "")

    # -----------------------------------------------------
    # 3. VALIDAR CAMPOS
    # -----------------------------------------------------

    if not video_id or not titulo:

        return JsonResponse(
            {
                "erro": "Os campos videoId e titulo são obrigatórios."
            },
            status=400
        )

    titulo_limpo = limpar_texto(titulo)
    cantor_limpo = limpar_texto(cantor)

    # -----------------------------------------------------
    # 4. VERIFICAR DUPLICIDADE
    # -----------------------------------------------------

    musica_existente = Musica.objects.filter(
        videoId=video_id
    ).first()

    if musica_existente:

        audio_existente = (
            settings.MEDIA_URL + str(musica_existente.audio)
            if musica_existente.audio
            else ""
        )

        return JsonResponse(
            {
                "status": "sucesso",
                "mensagem": "Música já processada anteriormente.",
                "id": musica_existente.id,
                "titulo": musica_existente.titulo,
                "videoId": musica_existente.videoId,
                "cantor": musica_existente.cantor,
                "audio_url": audio_existente,
            }
        )

    # -----------------------------------------------------
    # 5. CONFIGURAR PASTA DE ÁUDIO
    # -----------------------------------------------------

    pasta_audio = os.path.join(
        settings.MEDIA_ROOT,
        "audio"
    )

    os.makedirs(
        pasta_audio,
        exist_ok=True
    )

    nome_arquivo = str(video_id)

    caminho_absoluto_mp3 = os.path.join(
        pasta_audio,
        f"{nome_arquivo}.mp3"
    )

    caminho_relativo_django = (
        f"audio/{nome_arquivo}.mp3"
    )

    # -----------------------------------------------------
    # 6. CONFIGURAR YT-DLP
    # -----------------------------------------------------

    caminho_ffmpeg_projeto = os.path.join(
        settings.BASE_DIR,
        "ffmpeg_bin"
    )

    ydl_opts = {

        "format": "bestaudio/best",

        "outtmpl": os.path.join(
            pasta_audio,
            nome_arquivo + ".%(ext)s"
        ),

        "ffmpeg_location": caminho_ffmpeg_projeto,

        "source_address": "0.0.0.0",

        "nocheckcertificate": True,

        "ignoreerrors": False,

        "no_warnings": True,

        "quiet": True,

        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0.0.0 "
                "Safari/537.36"
            ),

            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),

            "Accept-Language": "en-us,en;q=0.5",

            "Sec-Fetch-Mode": "navigate",
        },

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
    }

    # -----------------------------------------------------
    # 7. BAIXAR ÁUDIO
    # -----------------------------------------------------

    audio_registrado = ""

    try:

        url_youtube = (
            f"https://www.youtube.com/watch?v={video_id}"
        )

        print(
            "🎬 INICIANDO DOWNLOAD DO ÁUDIO"
        )

        print(
            "🎵 Video ID:",
            video_id
        )

        print(
            "🔗 URL:",
            url_youtube
        )

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            ydl.download(
                [url_youtube]
            )

        # -------------------------------------------------
        # 8. VERIFICAR MP3
        # -------------------------------------------------

        if os.path.exists(
            caminho_absoluto_mp3
        ):

            audio_registrado = (
                caminho_relativo_django
            )

            print(
                "✅ MP3 CRIADO:",
                caminho_absoluto_mp3
            )

        else:

            print(
                "❌ MP3 NÃO FOI CRIADO:"
            )

            print(
                caminho_absoluto_mp3
            )

    except Exception as e:

        print(
            "❌ ERRO AO TENTAR EXTRAIR ÁUDIO:"
        )

        print(
            str(e)
        )

        return JsonResponse(
            {
                "erro": (
                    f"Falha no download/conversão: {str(e)}"
                )
            },
            status=500
        )

    # -----------------------------------------------------
    # 9. VERIFICAÇÃO FINAL
    # -----------------------------------------------------

    if not audio_registrado:

        return JsonResponse(
            {
                "erro": (
                    "A música foi recebida, "
                    "mas o arquivo MP3 não foi criado."
                ),

                "videoId": video_id,
            },
            status=500
        )

    # -----------------------------------------------------
    # 10. SALVAR NO BANCO
    # -----------------------------------------------------

    try:

        nova_musica = Musica.objects.create(

            titulo=titulo_limpo,

            videoId=video_id,

            cantor=cantor_limpo,

            audio=audio_registrado,
        )

    except Exception as e:

        print(
            "❌ ERRO AO SALVAR MÚSICA:"
        )

        print(
            str(e)
        )

        return JsonResponse(
            {
                "erro": (
                    f"Erro ao salvar música: {str(e)}"
                )
            },
            status=500
        )

    # -----------------------------------------------------
    # 11. MONTAR URL DO ÁUDIO
    # -----------------------------------------------------

    url_audio = (
        settings.MEDIA_URL + str(nova_musica.audio)
        if nova_musica.audio
        else ""
    )

    # -----------------------------------------------------
    # 12. RETORNAR
    # -----------------------------------------------------

    return JsonResponse(
        {
            "status": "sucesso",

            "id": nova_musica.id,

            "titulo": nova_musica.titulo,

            "videoId": nova_musica.videoId,

            "cantor": nova_musica.cantor,

            "audio_url": url_audio,
        },

        status=201
    )


# =========================================================
# NORMALIZAR TEXTO
# =========================================================

def normalizar_texto(texto):

    if not texto:
        return ""

    texto = str(texto).lower()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )

    palavras_ignoradas = [
        "karaoke",
        "musica",
        "ao vivo",
        "live",
        "instrumental",
        "playback",
        "versao",
        "cover",
        "original",
        "oficial",
    ]

    for palavra in palavras_ignoradas:

        texto = texto.replace(
            palavra,
            " "
        )

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    ).strip()

    return texto


# =========================================================
# PROCURAR ÁUDIO PARA UMA MÚSICA
# =========================================================

def encontrar_audio(titulo, cantor=""):

    pasta_audio = os.path.join(
        settings.MEDIA_ROOT,
        "audio"
    )

    print(
        "🔎 PROCURANDO ÁUDIO EM:",
        pasta_audio
    )

    if not os.path.exists(
        pasta_audio
    ):

        print(
            "⚠️ PASTA DE ÁUDIO NÃO EXISTE"
        )

        return ""

    extensoes_validas = (
        ".mp3",
        ".wav",
        ".ogg",
        ".m4a",
    )

    titulo_normalizado = normalizar_texto(
        titulo
    )

    cantor_normalizado = normalizar_texto(
        cantor
    )

    print(
        "🔎 TÍTULO NORMALIZADO:",
        titulo_normalizado
    )

    print(
        "🔎 CANTOR NORMALIZADO:",
        cantor_normalizado
    )

    palavras_titulo = [
        palavra
        for palavra in titulo_normalizado.split()
        if len(palavra) >= 3
    ]

    arquivos = os.listdir(
        pasta_audio
    )

    print(
        "🎧 ARQUIVOS DE ÁUDIO:",
        arquivos
    )

    # =====================================================
    # PRIMEIRA TENTATIVA
    # =====================================================

    if titulo_normalizado:

        for arquivo in arquivos:

            if not arquivo.lower().endswith(
                extensoes_validas
            ):
                continue

            nome_sem_extensao = os.path.splitext(
                arquivo
            )[0]

            nome_normalizado = normalizar_texto(
                nome_sem_extensao
            )

            if titulo_normalizado in nome_normalizado:

                print(
                    "🎵 ÁUDIO ENCONTRADO POR TÍTULO:",
                    arquivo
                )

                return arquivo

    # =====================================================
    # SEGUNDA TENTATIVA
    # =====================================================

    if palavras_titulo:

        melhor_arquivo = ""
        melhor_pontuacao = 0
        melhor_percentual = 0

        for arquivo in arquivos:

            if not arquivo.lower().endswith(
                extensoes_validas
            ):
                continue

            nome_sem_extensao = os.path.splitext(
                arquivo
            )[0]

            nome_normalizado = normalizar_texto(
                nome_sem_extensao
            )

            palavras_nome = set(
                nome_normalizado.split()
            )

            palavras_encontradas = [
                palavra
                for palavra in palavras_titulo
                if palavra in palavras_nome
            ]

            pontuacao = len(
                palavras_encontradas
            )

            percentual = (
                pontuacao / len(palavras_titulo)
            )

            print(
                "🔍 CANDIDATO:",
                arquivo
            )

            print(
                "   Palavras encontradas:",
                palavras_encontradas
            )

            print(
                "   Pontuação:",
                pontuacao,
                "/",
                len(palavras_titulo)
            )

            print(
                "   Percentual:",
                round(percentual * 100, 1),
                "%"
            )

            if (
                percentual > melhor_percentual
                or (
                    percentual == melhor_percentual
                    and pontuacao > melhor_pontuacao
                )
            ):

                melhor_arquivo = arquivo
                melhor_pontuacao = pontuacao
                melhor_percentual = percentual

        if len(palavras_titulo) == 1:

            if (
                melhor_arquivo
                and melhor_pontuacao == 1
            ):

                print(
                    "🎵 ÁUDIO ENCONTRADO POR PALAVRA ÚNICA:",
                    melhor_arquivo
                )

                return melhor_arquivo

        else:

            if (
                melhor_arquivo
                and melhor_percentual >= 0.70
            ):

                print(
                    "🎵 ÁUDIO ENCONTRADO POR CORRESPONDÊNCIA:",
                    melhor_arquivo
                )

                return melhor_arquivo

    # =====================================================
    # NENHUM ÁUDIO
    # =====================================================

    print(
        "🔎 NENHUM ÁUDIO SEGURO ENCONTRADO PARA:",
        titulo
    )

    return ""


# =========================================================
# SALVAR MÚSICA
# =========================================================

@csrf_exempt
def salvar_musica(request):

    # -----------------------------------------------------
    # 1. VALIDAR MÉTODO
    # -----------------------------------------------------

    if request.method != "POST":

        return JsonResponse(
            {
                "erro": "Método inválido. Use POST."
            },
            status=405
        )

    # -----------------------------------------------------
    # 2. CAPTURAR DADOS
    # -----------------------------------------------------

    try:

        if request.content_type == "application/json":

            dados = json.loads(
                request.body
            )

            video_id = dados.get(
                "videoId"
            )

            titulo = dados.get(
                "titulo"
            )

            cantor = dados.get(
                "cantor",
                ""
            )

        else:

            video_id = request.POST.get(
                "videoId"
            )

            titulo = request.POST.get(
                "titulo"
            )

            cantor = request.POST.get(
                "cantor",
                ""
            )

    except Exception as e:

        return JsonResponse(
            {
                "erro": (
                    f"Erro ao ler dados: {str(e)}"
                )
            },
            status=400
        )

    # -----------------------------------------------------
    # 3. VALIDAR CAMPOS
    # -----------------------------------------------------

    if not video_id or not titulo:

        return JsonResponse(
            {
                "erro": (
                    "videoId e titulo são obrigatórios."
                )
            },
            status=400
        )

    # -----------------------------------------------------
    # 4. VERIFICAR DUPLICIDADE
    # -----------------------------------------------------

    musica_existente = Musica.objects.filter(
        videoId=video_id
    ).first()

    if musica_existente:

        audio_existente = (
            settings.MEDIA_URL + str(musica_existente.audio)
            if musica_existente.audio
            else ""
        )

        return JsonResponse(
            {
                "status": "ok",

                "mensagem": "Música já cadastrada.",

                "id": musica_existente.id,

                "titulo": musica_existente.titulo,

                "videoId": musica_existente.videoId,

                "cantor": musica_existente.cantor,

                "audio": audio_existente,
            },
            status=200
        )

    # -----------------------------------------------------
    # 5. CONFIGURAR PASTA
    # -----------------------------------------------------

    pasta_audio = os.path.join(
        settings.MEDIA_ROOT,
        "audio"
    )

    os.makedirs(
        pasta_audio,
        exist_ok=True
    )

    # -----------------------------------------------------
    # 6. CONFIGURAR FFMPEG
    # -----------------------------------------------------

    caminho_ffmpeg_projeto = os.path.join(
        settings.BASE_DIR,
        "ffmpeg_bin"
    )

    # -----------------------------------------------------
    # 7. NOME DO ARQUIVO
    # -----------------------------------------------------

    nome_arquivo = str(
        video_id
    )

    caminho_absoluto_mp3 = os.path.join(
        pasta_audio,
        f"{nome_arquivo}.mp3"
    )

    caminho_relativo_django = (
        f"audio/{nome_arquivo}.mp3"
    )

    # -----------------------------------------------------
    # 8. CONFIGURAR YT-DLP
    # -----------------------------------------------------

    ydl_opts = {

        "format": "bestaudio/best",

        "outtmpl": os.path.join(
            pasta_audio,
            nome_arquivo + ".%(ext)s"
        ),

        "ffmpeg_location": (
            caminho_ffmpeg_projeto
        ),

        "source_address": "0.0.0.0",

        "nocheckcertificate": True,

        "ignoreerrors": False,

        "no_warnings": True,

        "quiet": True,

        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0.0.0 "
                "Safari/537.36"
            ),

            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),

            "Accept-Language": (
                "en-us,en;q=0.5"
            ),

            "Sec-Fetch-Mode": "navigate",
        },

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
    }

    # -----------------------------------------------------
    # 9. BAIXAR ÁUDIO
    # -----------------------------------------------------

    audio_registrado = ""

    try:

        url_youtube = (
            f"https://www.youtube.com/watch?v={video_id}"
        )

        print(
            "🎬 INICIANDO DOWNLOAD DO ÁUDIO"
        )

        print(
            "🎵 Video ID:",
            video_id
        )

        print(
            "🔗 URL:",
            url_youtube
        )

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.download(
                [url_youtube]
            )

        # -------------------------------------------------
        # 10. VERIFICAR MP3
        # -------------------------------------------------

        if os.path.exists(
            caminho_absoluto_mp3
        ):

            audio_registrado = (
                caminho_relativo_django
            )

            print(
                "✅ MP3 CRIADO:",
                caminho_absoluto_mp3
            )

        else:

            print(
                "❌ MP3 NÃO FOI CRIADO:"
            )

            print(
                caminho_absoluto_mp3
            )

    except Exception as e:

        print(
            "❌ ERRO AO TENTAR EXTRAIR ÁUDIO:"
        )

        print(
            str(e)
        )

        return JsonResponse(
            {
                "erro": (
                    f"Falha no download/conversão: {str(e)}"
                )
            },
            status=500
        )

    # -----------------------------------------------------
    # 11. VERIFICAÇÃO FINAL DO ÁUDIO
    # -----------------------------------------------------

    if not audio_registrado:

        return JsonResponse(
            {
                "erro": (
                    "A música foi recebida, "
                    "mas o arquivo MP3 não foi criado."
                ),

                "videoId": video_id,
            },
            status=500
        )

    # -----------------------------------------------------
    # 12. SALVAR NO BANCO
    # -----------------------------------------------------

    try:

        musica = Musica.objects.create(

            titulo=titulo,

            videoId=video_id,

            cantor=cantor,

            audio=audio_registrado
        )

    except Exception as e:

        print(
            "❌ ERRO AO SALVAR MÚSICA NO BANCO:"
        )

        print(
            str(e)
        )

        return JsonResponse(
            {
                "erro": (
                    f"Erro ao salvar música: {str(e)}"
                )
            },
            status=500
        )

    # -----------------------------------------------------
    # 13. URL DO ÁUDIO
    # -----------------------------------------------------

    url_audio_final = (
        settings.MEDIA_URL + str(musica.audio)
        if musica.audio
        else ""
    )

    # -----------------------------------------------------
    # 14. RETORNO PARA O REACT
    # -----------------------------------------------------

    return JsonResponse(
        {
            "status": "ok",

            "id": musica.id,

            "titulo": musica.titulo,

            "videoId": musica.videoId,

            "cantor": musica.cantor,

            "audio": url_audio_final,

        },
        status=201
    )


# =========================================================
# LISTAR MÚSICAS
# =========================================================

def listar_musicas(request):

    musicas = list(
        Musica.objects.all().values()
    )

    return JsonResponse(
        musicas,
        safe=False
    )


# =========================================================
# DELETAR MÚSICA
# =========================================================

@csrf_exempt
def deletar_musica(request, id):

    try:

        musica = Musica.objects.get(
            id=id
        )

        musica.delete()

        return JsonResponse(
            {
                "status": "ok"
            }
        )

    except Musica.DoesNotExist:

        return JsonResponse(
            {
                "erro": "não encontrada"
            },
            status=404
        )


# =========================================================
# RANKING
# =========================================================

def ranking(request):

    dados = (
        Musica.objects
        .values("cantor")
        .annotate(
            total=Count("id")
        )
        .order_by("-total")
    )

    return JsonResponse(
        list(dados),
        safe=False
    )


# =========================================================
# LISTAR ARQUIVOS DE ÁUDIO
# =========================================================

def listar_audios(request):

    pasta_audio = os.path.join(
        settings.MEDIA_ROOT,
        "audio"
    )

    if not os.path.exists(
        pasta_audio
    ):

        return JsonResponse(
            [],
            safe=False
        )

    arquivos = []

    for arquivo in os.listdir(
        pasta_audio
    ):

        if arquivo.lower().endswith(
            (
                ".mp3",
                ".wav",
                ".ogg",
                ".m4a"
            )
        ):

            arquivos.append(
                {
                    "nome": arquivo,

                    "url": (
                        settings.MEDIA_URL
                        + "audio/"
                        + arquivo
                    )
                }
            )

    arquivos.sort(
        key=lambda x:
        x["nome"].lower()
    )

    return JsonResponse(
        arquivos,
        safe=False
    )


# =========================================================
# ASSOCIAR ÁUDIO MANUALMENTE
# =========================================================

@csrf_exempt
def associar_audio(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "erro": "Use POST"
            },
            status=405
        )

    try:

        data = json.loads(
            request.body
        )

        video_id = data.get(
            "videoId"
        )

        nome_audio = data.get(
            "audio"
        )

        if not video_id or not nome_audio:

            return JsonResponse(
                {
                    "erro": (
                        "videoId e audio são obrigatórios"
                    )
                },
                status=400
            )

        musica = Musica.objects.filter(
            videoId=video_id
        ).first()

        if not musica:

            return JsonResponse(
                {
                    "erro": "Música não encontrada"
                },
                status=404
            )

        musica.audio = nome_audio

        musica.save()

        print(
            "🎧 ÁUDIO ASSOCIADO MANUALMENTE:",
            nome_audio
        )

        return JsonResponse(
            {
                "status": "ok",

                "titulo": musica.titulo,

                "videoId": musica.videoId,

                "audio": str(musica.audio)
            }
        )

    except Exception as e:

        print(
            "❌ ERRO ASSOCIAR AUDIO:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": str(e)
            },
            status=500
        )


# =========================================================
# BUSCAR ÁUDIO DA MÚSICA
# =========================================================

def audio_da_musica(
    request,
    video_id
):

    try:

        musica = Musica.objects.filter(
            videoId=video_id
        ).first()

        if not musica:

            return JsonResponse(
                {
                    "erro": "Música não encontrada"
                },
                status=404
            )

        # -------------------------------------------------
        # SE NÃO POSSUI ÁUDIO
        # -------------------------------------------------

        if not musica.audio:

            print(
                "🔎 Música sem áudio. Tentando localizar:"
            )

            audio = encontrar_audio(
                musica.titulo,
                musica.cantor
            )

            if audio:

                musica.audio = (
                    f"audio/{audio}"
                )

                musica.save()

                print(
                    "✅ ÁUDIO ENCONTRADO E ASSOCIADO:",
                    audio
                )

            else:

                return JsonResponse(
                    {
                        "erro": (
                            "Esta música ainda não "
                            "possui áudio associado"
                        )
                    },
                    status=404
                )

        # -------------------------------------------------
        # RETORNAR ÁUDIO
        # -------------------------------------------------

        url_audio = (
            settings.MEDIA_URL
            + str(musica.audio)
        )

        return JsonResponse(
            {
                "titulo": musica.titulo,

                "videoId": musica.videoId,

                "cantor": musica.cantor,

                "audio": str(musica.audio),

                "url": url_audio,
            }
        )

    except Exception as e:

        print(
            "❌ ERRO AO BUSCAR ÁUDIO:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": str(e)
            },
            status=500
        )