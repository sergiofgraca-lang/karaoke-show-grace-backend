import json
import os
import re
import unicodedata
import yt_dlp
from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from .models import Musica


def limpar_texto(texto):
    """Remove caracteres especiais e normaliza strings se necessário."""
    if not texto:
        return "Desconhecido"
    texto = (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode("utf-8")
    )
    return texto.strip()


@csrf_exempt
def processar_audio_youtube(request):
    # 1. VALIDAÇÃO DO MÉTODO DE ENTRADA
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido. Use POST."}, status=405)

    # 2. CAPTURA DOS PARÂMETROS (Suporta FormData do React ou JSON Puro)
    if request.content_type == "application/json":
        try:
            dados = json.loads(request.body)
            video_id = dados.get("videoId")
            titulo = dados.get("titulo")
            cantor = dados.get("cantor")
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido."}, status=400)
    else:
        video_id = request.POST.get("videoId")
        titulo = request.POST.get("titulo")
        cantor = request.POST.get("cantor")

    # 3. VALIDAÇÃO DOS CAMPOS OBRIGATÓRIOS
    if not video_id or not titulo:
        return JsonResponse(
            {"erro": "Os campos videoId e titulo são obrigatórios."}, status=400
        )

    # Limpeza básica dos dados recebidos
    titulo_limpo = limpar_texto(titulo)
    cantor_limpo = limpar_texto(cantor)

    # 4. VERIFICAÇÃO DE DUPLICIDADE NO BANCO
    musica_existente = Musica.objects.filter(videoId=video_id).first()
    if musica_existente:
        return JsonResponse(
            {
                "status": "sucesso",
                "mensagem": "Música já processada anteriormente.",
                "id": musica_existente.id,
                "audio_url": musica_existente.audio.url,
            }
        )

    # 5. CONFIGURAÇÃO DE PASTAS E ARQUIVOS (MEDIA)
    pasta_audio = os.path.join(settings.MEDIA_ROOT, "audio")
    os.makedirs(pasta_audio, exist_ok=True)

    # Identificador único baseado no videoId para evitar conflitos de arquivos
    nome_arquivo = f"{video_id}"
    caminho_absoluto_mp3 = os.path.join(pasta_audio, f"{nome_arquivo}.mp3")
    caminho_relativo_django = f"audio/{nome_arquivo}.mp3"

    # Configurações otimizadas do yt-dlp para conversão ágil
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(pasta_audio, nome_arquivo + ".%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    # 6. DOWNLOAD E EXTRAÇÃO DO ÁUDIO
    try:
        url_youtube = f"https://youtube.com{video_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_youtube])

        # Valida se o arquivo físico .mp3 foi devidamente gerado pelo FFmpeg
        if os.path.exists(caminho_absoluto_mp3):
            # Cria a associação definitiva no Banco de Dados
            nova_musica = Musica.objects.create(
                titulo=titulo_limpo,
                videoId=video_id,
                cantor=cantor_limpo,
                audio=caminho_relativo_django,
            )

            return JsonResponse(
                {"status": "sucesso", "audio_url": nova_musica.audio.url}
            )

        return JsonResponse(
            {"erro": "O FFmpeg não gerou o arquivo final MP3."}, status=500
        )

    except Exception as e:
        return JsonResponse(
            {"erro": f"Falha no download/conversão: {str(e)}"}, status=500
        )
# =========================================================
# NORMALIZAR TEXTO
# =========================================================

def normalizar_texto(texto):
    """
    Normaliza o texto para facilitar a comparação.

    Exemplo:

    "Roberto Carlos - Amada amante - Karaokê"
                         ↓
    "roberto carlos amada amante"
    """

    if not texto:
        return ""

    texto = str(texto).lower()

    # -----------------------------------------------------
    # Remove acentos
    # -----------------------------------------------------

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )

    # -----------------------------------------------------
    # Palavras que não ajudam na identificação
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Remove caracteres especiais
    # -----------------------------------------------------

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto
    )

    # -----------------------------------------------------
    # Remove espaços duplicados
    # -----------------------------------------------------

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

    if not os.path.exists(pasta_audio):

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

    # -----------------------------------------------------
    # Normalizar título e cantor
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Separar palavras do título
    # -----------------------------------------------------

    palavras_titulo = [
        palavra
        for palavra in titulo_normalizado.split()
        if len(palavra) >= 3
    ]

    palavras_cantor = [
        palavra
        for palavra in cantor_normalizado.split()
        if len(palavra) >= 3
    ]

    # -----------------------------------------------------
    # Listar arquivos
    # -----------------------------------------------------

    arquivos = os.listdir(
        pasta_audio
    )

    print(
        "🎧 ARQUIVOS DE ÁUDIO:",
        arquivos
    )

    # =====================================================
    # PRIMEIRA TENTATIVA
    #
    # Título completo dentro do nome do arquivo.
    #
    # Esta é a correspondência mais segura.
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

            print(
                "🔍 COMPARANDO TÍTULO:",
                titulo_normalizado,
                "<=>",
                nome_normalizado
            )

            if titulo_normalizado in nome_normalizado:

                print(
                    "🎵 ÁUDIO ENCONTRADO POR TÍTULO:",
                    arquivo
                )

                return arquivo

    # =====================================================
    # SEGUNDA TENTATIVA
    #
    # Comparação mais rigorosa.
    #
    # Não basta encontrar duas palavras.
    # Precisamos encontrar uma quantidade significativa
    # das palavras do título.
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

            # -------------------------------------------------
            # Palavras do título encontradas
            # -------------------------------------------------

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

            # -------------------------------------------------
            # Guardar melhor candidato
            # -------------------------------------------------

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

        # =====================================================
        # CRITÉRIO DE SEGURANÇA
        #
        # Títulos com 2 ou mais palavras:
        # pelo menos 70% das palavras precisam coincidir.
        #
        # Título com uma única palavra:
        # precisa coincidir exatamente.
        # =====================================================

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

                print(
                    "🎯 PONTUAÇÃO:",
                    melhor_pontuacao,
                    "/",
                    len(palavras_titulo)
                )

                print(
                    "🎯 PERCENTUAL:",
                    round(
                        melhor_percentual * 100,
                        1
                    ),
                    "%"
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

import os
import json
import yt_dlp
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Musica

@csrf_exempt
def salvar_musica(request):
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=405)

    # 1. CAPTURA DE DADOS
    try:
        if request.content_type == 'application/json':
            dados = json.loads(request.body)
            video_id = dados.get('videoId')
            titulo = dados.get('titulo')
            cantor = dados.get('cantor', '')
        else:
            video_id = request.POST.get('videoId')
            titulo = request.POST.get('titulo')
            cantor = request.POST.get('cantor', '')
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao ler dados: {str(e)}'}, status=400)

    if not video_id or not titulo:
        return JsonResponse({'erro': 'videoId e titulo são obrigatórios.'}, status=400)

    # Verificação de duplicados
    musica_existente = Musica.objects.filter(videoId=video_id).first()
    if musica_existente:
        return JsonResponse({
            "status": "ok",
            "id": musica_existente.id,
            "titulo": musica_existente.titulo,
            "videoId": musica_existente.videoId,
            "cantor": musica_existente.cantor,
            "audio": musica_existente.audio.url if musica_existente.audio else ""
        }, status=200)

    # 2. CONFIGURAÇÃO DE CAMINHOS
    pasta_audio = os.path.join(settings.MEDIA_ROOT, 'audio')
    os.makedirs(pasta_audio, exist_ok=True)

    caminho_ffmpeg_projeto = os.path.join(settings.BASE_DIR, 'ffmpeg_bin')
    nome_arquivo = f"{video_id}"
    caminho_absoluto_mp3 = os.path.join(pasta_audio, f"{nome_arquivo}.mp3")
    caminho_relativo_django = f"audio/{nome_arquivo}.mp3"

    # Configuração avançada anti-bloqueio do YouTube
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(pasta_audio, nome_arquivo + '.%(ext)s'),
        'ffmpeg_location': caminho_ffmpeg_projeto,
        
        # Parâmetros cruciais para burlar o bloqueio do YouTube e DNS no Windows:
        'source_address': '0.0.0.0', 
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'no_warnings': True,
        'quiet': True,
        
        # Força o yt-dlp a fingir que é um navegador comum acessando a página
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
    }

    # 3. DISPARO DO DOWNLOAD SEGURO
    audio_registrado = ""
    try:
        url_youtube = f"https://youtube.com{video_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_youtube])
        
        # Validamos se o arquivo físico foi criado com sucesso
        if os.path.exists(caminho_absoluto_mp3):
            audio_registrado = caminho_relativo_django
    except Exception as e:
        print(f"⚠️ Erro ao tentar extrair áudio: {str(e)}")

   


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
                "erro":
                "não encontrada"
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
                    "erro":
                    "videoId e audio são obrigatórios"
                },
                status=400
            )

        musica = Musica.objects.filter(
            videoId=video_id
        ).first()

        if not musica:

            return JsonResponse(
                {
                    "erro":
                    "Música não encontrada"
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
                "audio": musica.audio
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
                    "erro":
                    "Música não encontrada"
                },
                status=404
            )

        # -------------------------------------------------
        # Se a música existe mas ainda não possui áudio,
        # tenta encontrar novamente.
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

                musica.audio = audio

                musica.save()

                print(
                    "✅ ÁUDIO ENCONTRADO E ASSOCIADO:",
                    audio
                )

            else:

                return JsonResponse(
                    {
                        "erro":
                        "Esta música ainda não possui áudio associado"
                    },
                    status=404
                )

        # =================================================
        # RETORNAR ÁUDIO
        # =================================================

        return JsonResponse(
            {
                "titulo":
                musica.titulo,

                "videoId":
                musica.videoId,

                "cantor":
                musica.cantor,

                "audio":
                musica.audio,

                "url":
                settings.MEDIA_URL
                + "audio/"
                + musica.audio
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

