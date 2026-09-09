import json
import os
import re
import unicodedata
import yt_dlp
import imageio_ffmpeg
import requests
from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Musica

# =========================================================================
# CONFIGURAÇÃO SUPABASE STORAGE (AJUSTADA PARA O BUCKET 'audios')
# =========================================================================
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    ""
).rstrip("/")

SUPABASE_KEY = (
    os.environ.get("SUPABASE_KEY")
    or os.environ.get("SUPABASE_SECRET_KEY")
)

NOME_DO_BUCKET = "audios"  # <--- CORRIGIDO PARA O SEU BUCKET 'audios'
# =========================================================================

def limpar_texto(texto):
    if not texto:
        return "Desconhecido"
    texto = (
        unicodedata.normalize("NFKD", str(texto))
        .encode("ascii", "ignore")
        .decode("utf-8")
    )
    return texto.strip()

# =========================================================================
# BLOCO DE FUNÇÕES UTILITÁRIAS RESTAURADAS (LIMPEZA TOTAL DE ERROS)
# =========================================================================

def eh_url_supabase(url):
    if not url:
        return False
    return "supabase.co" in str(url)


def validar_video_id(video_id):
    """
    Valida se o formato do videoId do YouTube está correto (11 caracteres válidos).
    Resolve os erros das linhas 554 e 771.
    """
    if not video_id:
        return False
    # Padrão regex clássico para IDs do YouTube
    padrao = re.compile(r'^[a-zA-Z0-9_-]{11}$')
    return bool(padrao.match(str(video_id)))


def supabase_configurado():
    if not SUPABASE_URL:
        return False

    if not SUPABASE_KEY:
        return False

    return True


def gerar_url_assinada_supabase(video_id, segundos=3600):




    if not supabase_configurado():
        print("❌ Supabase não configurado.")
        return None

    caminho = f"{video_id}.mp3"

    url = (
    f"{SUPABASE_URL}"
    f"/storage/v1/object/sign/"
    f"{NOME_DO_BUCKET}/"
    f"{caminho}"
)

    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
    }

    dados = {
        "expiresIn": segundos
    }

    try:
        resposta = requests.post(
            url,
            headers=headers,
            json=dados,
            timeout=15
        )

        print(
            "🔐 Supabase assinatura HTTP:",
            resposta.status_code
        )

        if resposta.status_code >= 300:
            print(
                "❌ Erro ao gerar URL assinada:",
                resposta.text
            )
            return None

        resultado = resposta.json()

        signed_url = resultado.get("signedURL")

        if not signed_url:
            print(
                "❌ Supabase não retornou signedURL."
            )
            return None

        if signed_url.startswith("/object/"):
            signed_url = (
                SUPABASE_URL
                + "/storage/v1"
                + signed_url
            )
        elif signed_url.startswith("/"):
            signed_url = (
                SUPABASE_URL
                + signed_url
            )

        print(
            "✅ URL assinada gerada com sucesso."
        )

        return signed_url

    except Exception as e:
        print(
            "❌ Erro ao gerar URL assinada:",
            str(e)
        )
        return None


def audio_supabase_existe(video_id):
    """
    Verifica se o MP3 existe no bucket privado do Supabase.
    Gera uma URL assinada temporária e testa o arquivo.
    """

    if not video_id:
        return False

    try:
        signed_url = gerar_url_assinada_supabase(
            video_id,
            segundos=60
        )

        if not signed_url:
            print(
                "❌ Não foi possível gerar URL assinada para verificação."
            )
            return False

        print(
            "🔎 Testando arquivo através da URL assinada..."
        )

        resposta = requests.get(
            signed_url,
            headers={
                "Range": "bytes=0-0"
            },
            timeout=10
        )

        print(
            "🔎 Verificação pela URL assinada:",
            resposta.status_code
        )

        return resposta.status_code in (200, 206)

    except Exception as e:

        print(
            "❌ Erro verificando áudio no Supabase:",
            str(e)
        )

        return False

# =========================================================================


@csrf_exempt
def processar_audio_youtube(request, video_id=None):
    """
    Baixa o áudio do YouTube, converte para MP3 com FFmpeg,
    envia para o Supabase Storage privado e só então salva
    a música no banco de dados.

    Fluxo:

    YouTube
       ↓
    yt-dlp
       ↓
    arquivo temporário
       ↓
    FFmpeg → MP3
       ↓
    Supabase / audios / videoId.mp3
       ↓
    Neon / Musica
    """

    # ============================================================
    # 1. VALIDAR MÉTODO
    # ============================================================

    if request.method not in ["POST", "GET"]:

        return JsonResponse(
            {
                "erro": (
                    "Método inválido. "
                    "Use POST ou GET."
                )
            },
            status=405
        )

    # ============================================================
    # 2. RECEBER DADOS
    # ============================================================

    titulo = "Karaoke"
    cantor = ""

    if not video_id:

        if (
            request.content_type
            and
            request.content_type.startswith(
                "application/json"
            )
        ):

            try:

                dados = json.loads(
                    request.body
                )

                video_id = dados.get(
                    "videoId"
                )

                titulo = dados.get(
                    "titulo",
                    "Karaoke"
                )

                cantor = dados.get(
                    "cantor",
                    ""
                )

            except json.JSONDecodeError:

                return JsonResponse(
                    {
                        "erro": "JSON inválido."
                    },
                    status=400
                )

        else:

            video_id = request.POST.get(
                "videoId"
            )

            titulo = request.POST.get(
                "titulo",
                "Karaoke"
            )

            cantor = request.POST.get(
                "cantor",
                ""
            )

    else:

        titulo = request.GET.get(
            "titulo",
            "Karaoke"
        )

        cantor = request.GET.get(
            "cantor",
            ""
        )

    # ============================================================
    # 3. LIMPAR VIDEO ID
    # ============================================================

    video_id = str(
        video_id or ""
    ).strip()

    # ============================================================
    # 4. VALIDAR VIDEO ID
    # ============================================================

    if not validar_video_id(
        video_id
    ):

        return JsonResponse(
            {
                "erro": (
                    "ID do vídeo inválido "
                    "ou não encontrado."
                )
            },
            status=400
        )

    print(
        "🎬 Processando áudio do YouTube:",
        video_id
    )

    # ============================================================
    # 5. LIMPAR TEXTO
    # ============================================================

    titulo_limpo = limpar_texto(
        titulo
    )

    cantor_limpo = limpar_texto(
        cantor
    )

    # ============================================================
    # 6. VALIDAR SUPABASE
    # ============================================================

    if not supabase_configurado():

        print(
            "❌ Supabase não está configurado."
        )

        return JsonResponse(
            {
                "erro": (
                    "Supabase não está configurado."
                )
            },
            status=500
        )

    # ============================================================
    # 7. NOME DO ARQUIVO
    # ============================================================

    nome_arquivo = (
        f"{video_id}.mp3"
    )

    caminho_storage = (
        f"{NOME_DO_BUCKET}/{nome_arquivo}"
    )

    url_supabase_publica = (
        f"{SUPABASE_URL}"
        f"/storage/v1/object/public/"
        f"{caminho_storage}"
    )

    print(
        "📁 Arquivo destino:",
        nome_arquivo
    )

    # ============================================================
    # 8. VERIFICAR SE A MÚSICA JÁ EXISTE NO NEON
    # ============================================================

    musica_existente = (
        Musica.objects
        .filter(
            videoId=video_id
        )
        .first()
    )

    # ============================================================
    # 9. VERIFICAR SE O MP3 JÁ EXISTE NO SUPABASE
    # ============================================================

    arquivo_existe = False

    url_verificacao = (
        f"{SUPABASE_URL}"
        f"/storage/v1/object/"
        f"{NOME_DO_BUCKET}/"
        f"{nome_arquivo}"
    )

    headers_verificacao = {
        "Authorization": (
            f"Bearer {SUPABASE_KEY}"
        ),
        "apikey": SUPABASE_KEY,
    }

    try:

        resposta_verificacao = requests.head(
            url_verificacao,
            headers=headers_verificacao,
            timeout=10
        )

        print(
            "🔎 Verificação do arquivo no Supabase:",
            resposta_verificacao.status_code
        )

        if resposta_verificacao.status_code == 200:

            arquivo_existe = True

    except Exception as e:

        print(
            "⚠️ Não foi possível verificar "
            "o arquivo existente:",
            str(e)
        )

    # ============================================================
    # 10. SE O ARQUIVO JÁ EXISTE
    # ============================================================

    if arquivo_existe:

        print(
            "✅ MP3 já existe no Supabase:",
            nome_arquivo
        )

        if musica_existente:

            musica_existente.audio = (
                url_supabase_publica
            )

            musica_existente.titulo = (
                titulo_limpo
            )

            musica_existente.cantor = (
                cantor_limpo
            )

            musica_existente.save()

            musica = musica_existente

        else:

            musica = Musica.objects.create(
                titulo=titulo_limpo,
                videoId=video_id,
                cantor=cantor_limpo,
                audio=url_supabase_publica,
            )

        return JsonResponse(
            {
                "status": "sucesso",
                "id": musica.id,
                "titulo": musica.titulo,
                "videoId": musica.videoId,
                "cantor": musica.cantor,
                "audio": url_supabase_publica,
                "url": url_supabase_publica,
                "audio_url": url_supabase_publica
            },
            status=200
        )

    # ============================================================
    # 11. SE EXISTE NO NEON MAS NÃO EXISTE NO SUPABASE
    # ============================================================

    if musica_existente:

        print(
            "⚠️ Música existe no Neon, "
            "mas o MP3 não existe no Supabase."
        )

        print(
            "🔄 Vamos baixar o áudio novamente."
        )

    # ============================================================
    # 12. CRIAR DIRETÓRIO TEMPORÁRIO
    # ============================================================

    import tempfile

    pasta_temporaria = tempfile.mkdtemp(
        prefix="karaoke_audio_"
    )

    print(
        "📂 Pasta temporária:",
        pasta_temporaria
    )

    # ============================================================
    # 13. URL CORRETA DO YOUTUBE
    # ============================================================

    url_youtube = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    print(
        "🔗 URL YouTube:",
        url_youtube
    )

    # ============================================================
    # 14. CONFIGURAÇÃO DO YT-DLP
    # ============================================================

    ydl_opts = {

        "format": (
            "bestaudio/best"
        ),

        "outtmpl": os.path.join(
            pasta_temporaria,
            "%(id)s.%(ext)s"
        ),

        "noplaylist": True,

        "quiet": False,

        "no_warnings": False,

        "nocheckcertificate": True,

        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),

             "js_runtimes": {
            "node": {}
        },

        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    # ============================================================
    # 15. BAIXAR E CONVERTER PARA MP3
    # ============================================================

    caminho_mp3 = os.path.join(
        pasta_temporaria,
        f"{video_id}.mp3"
    )

    try:

        print(
            "⬇️ Baixando áudio do YouTube..."
        )

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            info = ydl.extract_info(
                url_youtube,
                download=True
            )

            print(
                "🎵 YouTube encontrado:",
                info.get(
                    "title",
                    "Sem título"
                )
            )

        # ========================================================
        # 16. CONFIRMAR MP3
        # ========================================================

        if not os.path.isfile(
            caminho_mp3
        ):

            print(
                "❌ FFmpeg não gerou o MP3 esperado:"
            )

            print(
                caminho_mp3
            )

            arquivos_temporarios = (
                os.listdir(
                    pasta_temporaria
                )
            )

            print(
                "📂 Arquivos encontrados:",
                arquivos_temporarios
            )

            return JsonResponse(
                {
                    "erro": (
                        "O áudio foi baixado, "
                        "mas o FFmpeg não gerou "
                        "o arquivo MP3."
                    )
                },
                status=500
            )

        # ========================================================
        # 17. TAMANHO DO MP3
        # ========================================================

        tamanho_mp3 = os.path.getsize(
            caminho_mp3
        )

        print(
            "✅ MP3 criado:"
        )

        print(
            "📄",
            caminho_mp3
        )

        print(
            "📦 Tamanho:",
            tamanho_mp3,
            "bytes"
        )

        if tamanho_mp3 <= 0:

            return JsonResponse(
                {
                    "erro": (
                        "O arquivo MP3 foi criado "
                        "mas está vazio."
                    )
                },
                status=500
            )

    except Exception as e:

        print(
            "❌ ERRO AO BAIXAR/CONVERTER:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": (
                    "Não foi possível baixar "
                    "ou converter o áudio: "
                    f"{str(e)}"
                )
            },
            status=500
        )

    # ============================================================
    # 18. ENVIAR MP3 PARA O SUPABASE
    # ============================================================

    url_upload_supabase = (
        f"{SUPABASE_URL}"
        f"/storage/v1/object/"
        f"{NOME_DO_BUCKET}/"
        f"{nome_arquivo}"
    )

    headers_upload = {

        "Authorization": (
            f"Bearer {SUPABASE_KEY}"
        ),

        "apikey": SUPABASE_KEY,

        "Content-Type": "audio/mpeg",

        "x-upsert": "true",
    }

    try:

        print(
            "☁️ Enviando MP3 para o Supabase..."
        )

        with open(
            caminho_mp3,
            "rb"
        ) as arquivo:

            dados_mp3 = arquivo.read()

        resposta_upload = requests.post(
            url_upload_supabase,
            headers=headers_upload,
            data=dados_mp3,
            timeout=60
        )

        print(
            "☁️ Supabase upload HTTP:",
            resposta_upload.status_code
        )

        if resposta_upload.status_code >= 300:

            print(
                "❌ Erro no upload para Supabase:"
            )

            print(
                resposta_upload.text[:1000]
            )

            return JsonResponse(
                {
                    "erro": (
                        "Não foi possível enviar "
                        "o MP3 para o Supabase."
                    ),
                    "status_supabase": (
                        resposta_upload.status_code
                    ),
                    "detalhes": (
                        resposta_upload.text[:500]
                    )
                },
                status=500
            )

        print(
            "✅ MP3 enviado para o Supabase:"
        )

        print(
            f"☁️ {NOME_DO_BUCKET}/{nome_arquivo}"
        )

    except Exception as e:

        print(
            "❌ ERRO NO UPLOAD SUPABASE:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": (
                    "Erro ao enviar áudio "
                    f"para o Supabase: {str(e)}"
                )
            },
            status=500
        )

    # ============================================================
    # 19. CONFIRMAR NOVAMENTE QUE O ARQUIVO EXISTE
    # ============================================================

    arquivo_confirmado = False

    try:

        resposta_confirmacao = requests.head(
            url_verificacao,
            headers=headers_verificacao,
            timeout=10
        )

        print(
            "🔍 Confirmação do upload:",
            resposta_confirmacao.status_code
        )

        arquivo_confirmado = (
            resposta_confirmacao.status_code == 200
        )

    except Exception as e:

        print(
            "⚠️ Erro ao confirmar upload:",
            str(e)
        )

    if not arquivo_confirmado:

        print(
            "❌ O Supabase não confirmou "
            "a existência do MP3."
        )

        return JsonResponse(
            {
                "erro": (
                    "O upload foi enviado, "
                    "mas o arquivo não pôde "
                    "ser confirmado no Supabase."
                )
            },
            status=500
        )

    print(
        "✅ Arquivo confirmado no Supabase."
    )

    # ============================================================
    # 20. AGORA SIM SALVAR NO NEON
    # ============================================================

    try:

        if musica_existente:

            musica_existente.titulo = (
                titulo_limpo
            )

            musica_existente.cantor = (
                cantor_limpo
            )

            musica_existente.audio = (
                url_supabase_publica
            )

            musica_existente.save()

            nova_musica = (
                musica_existente
            )

            print(
                "✅ Música existente atualizada no Neon."
            )

        else:

            nova_musica = (
                Musica.objects.create(
                    titulo=titulo_limpo,
                    videoId=video_id,
                    cantor=cantor_limpo,
                    audio=url_supabase_publica,
                )
            )

            print(
                "✅ Nova música salva no Neon."
            )

    except Exception as e:

        print(
            "❌ ERRO AO SALVAR NO NEON:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": (
                    "O áudio foi enviado para "
                    "o Supabase, mas ocorreu "
                    "um erro ao salvar a música "
                    f"no Neon: {str(e)}"
                )
            },
            status=500
        )

    # ============================================================
    # 21. RESPOSTA FINAL
    # ============================================================

    print(
        "🎉 PROCESSAMENTO CONCLUÍDO:"
    )

    print(
        "🎵 Música:",
        nova_musica.titulo
    )

    print(
        "🆔 VideoId:",
        nova_musica.videoId
    )

    print(
        "☁️ Arquivo:",
        nome_arquivo
    )

    print(
        "🔐 Storage:",
        NOME_DO_BUCKET
    )

    return JsonResponse(
        {
            "status": "sucesso",

            "id": nova_musica.id,

            "titulo": nova_musica.titulo,

            "videoId": nova_musica.videoId,

            "cantor": nova_musica.cantor,

            "audio": url_supabase_publica,

            "url": url_supabase_publica,

            "audio_url": url_supabase_publica
        },
        status=201
    )



# ============================================================
# LISTAR MÚSICAS
# ============================================================

def listar_musicas(request):

    if request.method != "GET":

        return JsonResponse(
            {
                "erro": (
                    "Método inválido. "
                    "Use GET."
                )
            },
            status=405
        )

    try:

        musicas = (
            Musica.objects
            .all()
            .order_by("-id")
        )

        resultado = []

        for musica in musicas:

            audio = ""

            if musica.audio:

                audio = str(
                    musica.audio
                ).strip()

                # Nunca devolver Vevioz.
                if (
                    "vevioz.com"
                    in audio.lower()
                ):

                    audio = ""

            resultado.append(
                {
                    "id": musica.id,

                    "titulo": (
                        musica.titulo
                    ),

                    "videoId": (
                        musica.videoId
                    ),

                    "cantor": (
                        musica.cantor
                    ),

                    "audio": audio
                }
            )

        return JsonResponse(
            resultado,
            safe=False
        )

    except Exception as e:

        print(
            "❌ ERRO AO LISTAR MÚSICAS:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": str(e)
            },
            status=500
        )


# ============================================================
# DELETAR MÚSICA
# ============================================================

@csrf_exempt
def deletar_musica(
    request,
    id
):

    if request.method != "DELETE":

        return JsonResponse(
            {
                "erro": (
                    "Método inválido. "
                    "Use DELETE."
                )
            },
            status=405
        )

    try:

        musica = (
            Musica.objects
            .filter(
                id=id
            )
            .first()
        )

        if not musica:

            return JsonResponse(
                {
                    "erro": (
                        "Música não encontrada."
                    )
                },
                status=404
            )

        musica.delete()

        return JsonResponse(
            {
                "status": "sucesso",

                "mensagem": (
                    "Música deletada."
                )
            }
        )

    except Exception as e:

        print(
            "❌ ERRO AO DELETAR:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": str(e)
            },
            status=500
        )


# ============================================================
# RANKING
# ============================================================

def ranking(request):

    if request.method != "GET":

        return JsonResponse(
            {
                "erro": (
                    "Método inválido. "
                    "Use GET."
                )
            },
            status=405
        )

    try:

        ranking_musicas = (

            Musica.objects

            .values(
                "titulo",
                "videoId"
            )

            .annotate(
                total=Count("id")
            )

            .order_by(
                "-total"
            )
        )

        return JsonResponse(
            list(
                ranking_musicas
            ),
            safe=False
        )

    except Exception as e:

        print(
            "❌ ERRO NO RANKING:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": str(e)
            },
            status=500
        )


# ============================================================
# LISTAR ÁUDIOS LOCAIS
# ============================================================

def listar_audios(request):

    if request.method != "GET":

        return JsonResponse(
            {
                "erro": (
                    "Método inválido. "
                    "Use GET."
                )
            },
            status=405
        )

    try:

        audio_dir = os.path.join(
            settings.MEDIA_ROOT,
            "audio"
        )

        if not os.path.exists(
            audio_dir
        ):

            return JsonResponse(
                [],
                safe=False
            )

        extensoes = [

            ".mp3",

            ".wav",

            ".ogg",

            ".m4a"

        ]

        arquivos = []

        for arquivo in os.listdir(
            audio_dir
        ):

            extensao = (
                os.path.splitext(
                    arquivo
                )[1]
                .lower()
            )

            if extensao in extensoes:

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

        return JsonResponse(
            arquivos,
            safe=False
        )

    except Exception as e:

        print(
            "❌ ERRO AO LISTAR ÁUDIOS:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": str(e)
            },
            status=500
        )


# ============================================================
# ASSOCIAR ÁUDIO
# ============================================================

@csrf_exempt
def associar_audio(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "erro": (
                    "Método inválido. "
                    "Use POST."
                )
            },
            status=405
        )

    # --------------------------------------------------------
    # RECEBER DADOS
    # --------------------------------------------------------

    try:

        if (
            request.content_type
            and
            request.content_type.startswith(
                "application/json"
            )
        ):

            dados = json.loads(
                request.body
            )

            video_id = dados.get(
                "videoId"
            )

            audio = dados.get(
                "audio"
            )

        else:

            video_id = request.POST.get(
                "videoId"
            )

            audio = request.POST.get(
                "audio"
            )

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "erro": "JSON inválido."
            },
            status=400
        )

    # --------------------------------------------------------
    # LIMPAR
    # --------------------------------------------------------

    video_id = (
        str(video_id or "")
        .strip()
    )

    audio = (
        str(audio or "")
        .strip()
    )

    # --------------------------------------------------------
    # VALIDAR VIDEO ID
    # --------------------------------------------------------

    if not validar_video_id(
    video_id
):

     return JsonResponse(
        {
            "erro": (
                "videoId inválido."
            )
        },
        status=400
    )

    # --------------------------------------------------------
    # VALIDAR ÁUDIO
    # --------------------------------------------------------

    if not audio:

        return JsonResponse(
            {
                "erro": (
                    "audio é obrigatório."
                )
            },
            status=400
        )

    # --------------------------------------------------------
    # IMPEDIR VEVIOZ
    # --------------------------------------------------------

    if (
        "vevioz.com"
        in audio.lower()
    ):

        return JsonResponse(
            {
                "erro": (
                    "URL de áudio inválida. "
                    "Vevioz não é uma fonte "
                    "de áudio válida."
                )
            },
            status=400
        )

    # --------------------------------------------------------
    # LOCALIZAR MÚSICA
    # --------------------------------------------------------

    try:

        musica = (
            Musica.objects
            .filter(
                videoId=video_id
            )
            .first()
        )

        if not musica:

            return JsonResponse(
                {
                    "erro": (
                        "Música não encontrada."
                    )
                },
                status=404
            )

        musica.audio = audio

        musica.save(
            update_fields=[
                "audio"
            ]
        )

        print(
            "✅ Áudio associado:",
            audio
        )

        return JsonResponse(
            {
                "status": "sucesso",

                "mensagem": (
                    "Áudio associado "
                    "com sucesso."
                ),

                "videoId": (
                    musica.videoId
                ),

                "audio": musica.audio
            }
        )

    except Exception as e:

        print(
            "❌ ERRO AO ASSOCIAR ÁUDIO:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": str(e)
            },
            status=500
        )


# ============================================================
# ENCONTRAR ÁUDIO LOCAL
# ============================================================

def encontrar_audio(video_id):

    video_id = (
        str(video_id or "")
        .strip()
    )

    if not video_id:
        return None

    audio_dir = os.path.join(
        settings.MEDIA_ROOT,
        "audio"
    )

    if not os.path.exists(
        audio_dir
    ):

        return None

    extensoes = [

        ".mp3",

        ".wav",

        ".ogg",

        ".m4a"

    ]

    # --------------------------------------------------------
    # PROCURAR PELO NOME EXATO
    # --------------------------------------------------------

    for extensao in extensoes:

        nome = (
            video_id
            + extensao
        )

        caminho = os.path.join(
            audio_dir,
            nome
        )

        if os.path.isfile(
            caminho
        ):

            return (
                "audio/"
                + nome
            )

    # --------------------------------------------------------
    # NÃO ENCONTROU
    # --------------------------------------------------------

    return None


# ============================================================
# BUSCAR ÁUDIO DE UMA MÚSICA
# ============================================================

def servir_audio_supabase(request, video_id):
    """
    Entrega o MP3 privado do Supabase através do Django.
    """

    if request.method != "GET":
        return JsonResponse(
            {"erro": "Método não permitido."},
            status=405
        )

    if not video_id:
        return JsonResponse(
            {"erro": "videoId não informado."},
            status=400
        )

    print(
        "🎧 Servindo áudio pelo Django:",
        video_id
    )

    # Gera uma URL temporária para o arquivo privado
    signed_url = gerar_url_assinada_supabase(
        video_id,
        segundos=3600
    )

    print("🔗 URL assinada:", signed_url)

    if not signed_url:
        print(
            "❌ Não foi possível gerar URL do áudio."
        )

        return JsonResponse(
            {"erro": "Áudio não encontrado."},
            status=404
        )

    try:
        resposta = requests.get(
            signed_url,
            timeout=30
        )

        print(
            "📥 Supabase respondeu:",
            resposta.status_code,
            "Tamanho:",
            len(resposta.content)
        )

        if resposta.status_code != 200:
            print(
                "❌ Erro ao baixar áudio do Supabase:",
                resposta.text[:500]
            )

            return JsonResponse(
                {"erro": "Não foi possível obter o áudio."},
                status=404
            )

        response = HttpResponse(
            resposta.content,
            content_type="audio/mpeg"
        )

        response["Content-Length"] = str(
            len(resposta.content)
        )

        response["Cache-Control"] = "no-cache"

        return response

    except Exception as e:
        print(
            "❌ Erro servindo áudio:",
            str(e)
        )

        return JsonResponse(
            {"erro": "Erro interno ao carregar áudio."},
            status=500
        )


def audio_da_musica(
    request,
    video_id
):

    if request.method != "GET":

        return JsonResponse(
            {
                "erro": (
                    "Método inválido. "
                    "Use GET."
                )
            },
            status=405
        )

    # --------------------------------------------------------
    # VALIDAR VIDEO ID
    # --------------------------------------------------------

    

    if not validar_video_id(
    video_id
):

       return JsonResponse(
        {
            "erro": "videoId inválido."
        },
        status=400
        )

    print(
        "🔎 Procurando áudio associado ao videoId:",
        video_id
    )

    # --------------------------------------------------------
    # BUSCAR MÚSICA
    # --------------------------------------------------------

    try:

        musica = (
            Musica.objects
            .filter(
                videoId=video_id
            )
            .first()
        )

    except Exception as e:

        print(
            "❌ ERRO AO BUSCAR MÚSICA:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": str(e)
            },
            status=500
        )

    # --------------------------------------------------------
    # MÚSICA NÃO EXISTE
    # --------------------------------------------------------

    if not musica:

        return JsonResponse(
            {
                "erro": (
                    "Música não encontrada."
                ),

                "videoId": video_id
            },
            status=404
        )

    # ========================================================
    # VERIFICAR ÁUDIO SALVO
    # ========================================================

    if musica.audio:

        audio = str(
            musica.audio
        ).strip()

        # ----------------------------------------------------
        # NUNCA ACEITAR VEVIOZ
        # ----------------------------------------------------

        if (
            "vevioz.com"
            in audio.lower()
        ):

            print(
                "🧹 Removendo URL falsa do Vevioz."
            )

            musica.audio = ""

            musica.save(
                update_fields=[
                    "audio"
                ]
            )

            audio = ""

        # ----------------------------------------------------
        # URL ABSOLUTA
        # ----------------------------------------------------

        elif (
            audio.startswith(
                "http://"
            )
            or
            audio.startswith(
                "https://"
            )
        ):

            print(
                "🔗 Áudio remoto encontrado:",
                audio
            )

            # ------------------------------------------------
            # SE FOR SUPABASE, VERIFICAR ARQUIVO
            # ------------------------------------------------

            if eh_url_supabase(
                audio
            ):

                if audio_supabase_existe(
                    video_id
                ):

                    print(
                        "✅ Arquivo confirmado no Supabase."
                    )

                    return JsonResponse(
                        {
                            "status": "sucesso",

                            "titulo": (
                                musica.titulo
                            ),

                            "videoId": (
                                musica.videoId
                            ),

                            "audio": audio,

                            "url": audio,

                            "audio_url": audio
                        }
                    )

                print(
                    "⚠️ URL existe no Neon, "
                    "mas arquivo não foi encontrado no Supabase."
                )

                musica.audio = ""

                musica.save(
                    update_fields=[
                        "audio"
                    ]
                )

            else:

                # ------------------------------------------------
                # URLs externas que não sejam Vevioz.
                # ------------------------------------------------

                return JsonResponse(
                    {
                        "status": "sucesso",

                        "titulo": (
                            musica.titulo
                        ),

                        "videoId": (
                            musica.videoId
                        ),

                        "audio": audio,

                        "url": audio,

                        "audio_url": audio
                    }
                )

        # ----------------------------------------------------
        # CAMINHO LOCAL
        # ----------------------------------------------------

        else:

            if audio.startswith(
                "media/"
            ):

                audio = audio[
                    len("media/"):
                ]

            audio = audio.lstrip(
                "/"
            )

            caminho_local = os.path.join(
                settings.MEDIA_ROOT,
                audio
            )

            if os.path.isfile(
                caminho_local
            ):

                url_audio = (
                    settings.MEDIA_URL
                    + audio
                )

                print(
                    "✅ Áudio local encontrado:",
                    url_audio
                )

                return JsonResponse(
                    {
                        "status": "sucesso",

                        "titulo": (
                            musica.titulo
                        ),

                        "videoId": (
                            musica.videoId
                        ),

                        "audio": url_audio,

                        "url": url_audio,

                        "audio_url": url_audio
                    }
                )

            print(
                "⚠️ Caminho local não existe:",
                caminho_local
            )

            musica.audio = ""

            musica.save(
                update_fields=[
                    "audio"
                ]
            )

    # ========================================================
    # PROCURAR ÁUDIO LOCAL
    # ========================================================

    audio_local = encontrar_audio(
        video_id
    )

    if audio_local:

        print(
            "🎵 Áudio local encontrado:",
            audio_local
        )

        musica.audio = audio_local

        musica.save(
            update_fields=[
                "audio"
            ]
        )

        url_audio = (
            settings.MEDIA_URL
            + audio_local
        )

        return JsonResponse(
            {
                "status": "sucesso",

                "titulo": (
                    musica.titulo
                ),

                "videoId": (
                    musica.videoId
                ),

                "audio": url_audio,

                "url": url_audio,

                "audio_url": url_audio
            }
        )

    # ========================================================
    # NENHUM ÁUDIO REAL
    # ========================================================

    print(
        "⚠️ Música ainda não possui áudio real."
    )

    return JsonResponse(
        {
            "status": "sem_audio",

            "erro": (
                "Esta música ainda não possui "
                "um áudio real associado."
            ),

            "titulo": (
                musica.titulo
            ),

            "videoId": video_id,

            "audio": "",

            "url": "",

            "audio_url": ""
        },
        status=404
    )

