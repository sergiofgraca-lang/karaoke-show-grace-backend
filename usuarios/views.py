import json
import os
import re
import tempfile
import unicodedata

import requests
import yt_dlp

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count

from .models import Musica


# ============================================================
# CONFIGURAÇÃO SUPABASE
# ============================================================

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    ""
).rstrip("/")

# Aceita os dois nomes de variável.
#
# Preferência:
# SUPABASE_KEY
#
# Compatibilidade com configuração anterior:
# SUPABASE_SECRET_KEY
#
SUPABASE_KEY = (
    os.environ.get("SUPABASE_KEY")
    or os.environ.get("SUPABASE_SECRET_KEY")
)

# NOME CORRETO DO BUCKET
NOME_DO_BUCKET = "audios"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def limpar_texto(texto):

    if not texto:
        return "Desconhecido"

    texto = (
        unicodedata.normalize(
            "NFKD",
            str(texto)
        )
        .encode(
            "ascii",
            "ignore"
        )
        .decode(
            "utf-8"
        )
    )

    return texto.strip()


def validar_video_id(video_id):

    if not video_id:
        return None

    video_id = str(video_id).strip()

    # ID normal do YouTube possui 11 caracteres
    if not re.fullmatch(
        r"[A-Za-z0-9_-]{11}",
        video_id
    ):
        return None

    return video_id


def url_supabase_audio(video_id):

    return (
        f"{SUPABASE_URL}"
        f"/storage/v1/object/public/"
        f"{NOME_DO_BUCKET}/"
        f"{video_id}.mp3"
    )


def url_upload_supabase(video_id):

    return (
        f"{SUPABASE_URL}"
        f"/storage/v1/object/"
        f"{NOME_DO_BUCKET}/"
        f"{video_id}.mp3"
    )


def supabase_configurado():

    if not SUPABASE_URL:
        return False

    if not SUPABASE_KEY:
        return False

    return True


def eh_url_supabase(audio):

    if not audio:
        return False

    audio = str(audio).strip()

    if not SUPABASE_URL:
        return False

    url_base = (
        f"{SUPABASE_URL}"
        f"/storage/v1/object/public/"
        f"{NOME_DO_BUCKET}/"
    )

    return audio.startswith(url_base)


def audio_supabase_existe(video_id):

    if not supabase_configurado():
        return False

    url = url_supabase_audio(
        video_id
    )

    try:

        resposta = requests.head(
            url,
            timeout=10
        )

        if resposta.status_code == 200:
            return True

    except Exception as e:

        print(
            "⚠️ Erro verificando áudio no Supabase:",
            str(e)
        )

    return False


# ============================================================
# PROCESSAR ÁUDIO DO YOUTUBE
# ============================================================

@csrf_exempt
def processar_audio_youtube(request):

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

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "erro": "JSON inválido."
            },
            status=400
        )

    # --------------------------------------------------------
    # VALIDAR VIDEO ID
    # --------------------------------------------------------

    video_id = validar_video_id(
        video_id
    )

    if not video_id:

        return JsonResponse(
            {
                "erro": (
                    "videoId inválido. "
                    "O ID do YouTube deve possuir "
                    "11 caracteres."
                )
            },
            status=400
        )

    # --------------------------------------------------------
    # VALIDAR TÍTULO
    # --------------------------------------------------------

    if not titulo:

        return JsonResponse(
            {
                "erro": (
                    "Os campos videoId e titulo "
                    "são obrigatórios."
                )
            },
            status=400
        )

    titulo_limpo = limpar_texto(
        titulo
    )

    cantor_limpo = limpar_texto(
        cantor
    )

    # --------------------------------------------------------
    # VERIFICAR SUPABASE
    # --------------------------------------------------------

    if not supabase_configurado():

        print(
            "❌ SUPABASE NÃO CONFIGURADO."
        )

        return JsonResponse(
            {
                "erro": (
                    "Supabase não está configurado "
                    "corretamente no servidor."
                )
            },
            status=500
        )

    # --------------------------------------------------------
    # URLs DO ARQUIVO
    # --------------------------------------------------------

    nome_arquivo = (
        f"{video_id}.mp3"
    )

    url_publica = url_supabase_audio(
        video_id
    )

    url_upload = url_upload_supabase(
        video_id
    )

    print(
        "🎵 Processando música:",
        titulo_limpo
    )

    print(
        "🆔 Video ID:",
        video_id
    )

    print(
        "📦 Arquivo:",
        nome_arquivo
    )

    print(
        "☁️ Bucket:",
        NOME_DO_BUCKET
    )

    # --------------------------------------------------------
    # PROCURAR MÚSICA EXISTENTE
    # --------------------------------------------------------

    try:

        musica_existente = (
            Musica.objects
            .filter(
                videoId=video_id
            )
            .first()
        )

    except Exception as e:

        print(
            "❌ ERRO AO CONSULTAR NEON:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": (
                    "Erro ao consultar banco de dados: "
                    + str(e)
                )
            },
            status=500
        )

    # --------------------------------------------------------
    # SE JÁ EXISTE E O ÁUDIO REAL ESTÁ NO SUPABASE
    # NÃO PRECISAMOS BAIXAR NOVAMENTE
    # --------------------------------------------------------

    if musica_existente:

        audio_existente = str(
            musica_existente.audio or ""
        ).strip()

        print(
            "🔎 Música já existe no Neon."
        )

        print(
            "🔊 Áudio salvo:",
            audio_existente
        )

        if (
            eh_url_supabase(
                audio_existente
            )
            and
            audio_supabase_existe(
                video_id
            )
        ):

            print(
                "✅ Áudio já existe no Supabase."
            )

            return JsonResponse(
                {
                    "status": "sucesso",
                    "id": musica_existente.id,
                    "titulo": musica_existente.titulo,
                    "videoId": musica_existente.videoId,
                    "cantor": musica_existente.cantor,
                    "audio": url_publica,
                    "url": url_publica,
                    "audio_url": url_publica
                }
            )

        print(
            "⚠️ Registro existe, "
            "mas o áudio real precisa ser processado."
        )

    # ========================================================
    # DOWNLOAD E CONVERSÃO
    # ========================================================

    arquivo_mp3 = None
    arquivo_base = None

    try:

        # ----------------------------------------------------
        # DIRETÓRIO TEMPORÁRIO
        # ----------------------------------------------------

        diretorio_temp = tempfile.mkdtemp(
            prefix="karaoke_"
        )

        arquivo_base = os.path.join(
            diretorio_temp,
            video_id
        )

        arquivo_mp3 = (
            arquivo_base
            + ".mp3"
        )

        print(
            "📁 Diretório temporário:",
            diretorio_temp
        )

        # ----------------------------------------------------
        # URL CORRETA DO YOUTUBE
        # ----------------------------------------------------

        url_youtube = (
            "https://www.youtube.com/watch?v="
            + video_id
        )

        print(
            "🔎 YouTube:",
            url_youtube
        )

        # ----------------------------------------------------
        # CONFIGURAÇÃO YT-DLP
        # ----------------------------------------------------

        ydl_opts = {

            # Preferimos áudio.
            "format": (
                "bestaudio/"
                "best"
            ),

            # Arquivo temporário.
            "outtmpl": (
                arquivo_base
                + ".%(ext)s"
            ),

            # Converter para MP3.
            "postprocessors": [

                {
                    "key": (
                        "FFmpegExtractAudio"
                    ),
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }

            ],

            "quiet": True,

            "no_warnings": True,

            # Não deixar playlist interferir.
            "noplaylist": True,

            # Tentativas.
            "retries": 2,

            "fragment_retries": 2,

            # Evita alguns problemas de certificado.
            "nocheckcertificate": True
        }

        # ----------------------------------------------------
        # BAIXAR
        # ----------------------------------------------------

        print(
            "⬇️ Baixando áudio com yt-dlp..."
        )

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            info = ydl.extract_info(
                url_youtube,
                download=True
            )

        print(
            "✅ Download concluído."
        )

        # ----------------------------------------------------
        # LOCALIZAR MP3 GERADO
        # ----------------------------------------------------

        if not os.path.exists(
            arquivo_mp3
        ):

            print(
                "⚠️ MP3 não encontrado "
                "no caminho esperado."
            )

            # Procurar qualquer MP3
            # no diretório temporário.

            arquivos_temp = os.listdir(
                diretorio_temp
            )

            print(
                "📂 Arquivos temporários:",
                arquivos_temp
            )

            for arquivo in arquivos_temp:

                if arquivo.lower().endswith(
                    ".mp3"
                ):

                    arquivo_mp3 = os.path.join(
                        diretorio_temp,
                        arquivo
                    )

                    break

        # ----------------------------------------------------
        # VALIDAR MP3
        # ----------------------------------------------------

        if not os.path.exists(
            arquivo_mp3
        ):

            raise Exception(
                "O yt-dlp não gerou o arquivo MP3."
            )

        tamanho_mp3 = os.path.getsize(
            arquivo_mp3
        )

        print(
            "🎧 MP3 gerado:",
            arquivo_mp3
        )

        print(
            "📏 Tamanho:",
            tamanho_mp3,
            "bytes"
        )

        if tamanho_mp3 <= 0:

            raise Exception(
                "O arquivo MP3 foi gerado vazio."
            )

        # ====================================================
        # UPLOAD SUPABASE
        # ====================================================

        print(
            "☁️ Enviando MP3 para Supabase..."
        )

        headers_supabase = {

            "Authorization": (
                f"Bearer {SUPABASE_KEY}"
            ),

            "apikey": SUPABASE_KEY,

            "Content-Type": "audio/mpeg",

            "x-upsert": "true"
        }

        with open(
            arquivo_mp3,
            "rb"
        ) as arquivo:

            upload_req = requests.post(

                url_upload,

                headers=headers_supabase,

                data=arquivo,

                timeout=60
            )

        print(
            "☁️ Supabase HTTP:",
            upload_req.status_code
        )

        # ----------------------------------------------------
        # VALIDAR UPLOAD
        # ----------------------------------------------------

        if upload_req.status_code >= 300:

            print(
                "❌ Erro retornado pelo Supabase:"
            )

            print(
                upload_req.text
            )

            return JsonResponse(
                {
                    "erro": (
                        "Erro ao enviar o MP3 "
                        "para o Supabase."
                    ),
                    "status_supabase": (
                        upload_req.status_code
                    ),
                    "detalhes": (
                        upload_req.text
                    )
                },
                status=500
            )

        print(
            "✅ MP3 enviado para Supabase."
        )

        print(
            "🔗 URL pública:",
            url_publica
        )

    except Exception as e:

        print(
            "❌ ERRO AO PROCESSAR ÁUDIO:"
        )

        print(
            str(e)
        )

        return JsonResponse(
            {
                "erro": (
                    "Não foi possível processar "
                    "o áudio do YouTube."
                ),
                "detalhes": str(e)
            },
            status=500
        )

    finally:

        # ----------------------------------------------------
        # LIMPAR ARQUIVOS TEMPORÁRIOS
        # ----------------------------------------------------

        try:

            if (
                diretorio_temp
                and
                os.path.exists(
                    diretorio_temp
                )
            ):

                import shutil

                shutil.rmtree(
                    diretorio_temp,
                    ignore_errors=True
                )

                print(
                    "🧹 Arquivos temporários removidos."
                )

        except Exception as e:

            print(
                "⚠️ Não foi possível limpar "
                "temporários:",
                str(e)
            )

    # ========================================================
    # SALVAR NO NEON
    # ========================================================

    try:

        if musica_existente:

            musica_existente.titulo = (
                titulo_limpo
            )

            musica_existente.cantor = (
                cantor_limpo
            )

            musica_existente.audio = (
                url_publica
            )

            musica_existente.save()

            musica = musica_existente

            print(
                "✅ Música existente atualizada no Neon."
            )

        else:

            musica = Musica.objects.create(

                titulo=titulo_limpo,

                videoId=video_id,

                cantor=cantor_limpo,

                audio=url_publica
            )

            print(
                "✅ Nova música criada no Neon."
            )

    except Exception as e:

        print(
            "❌ ERRO AO SALVAR NO NEON:",
            str(e)
        )

        return JsonResponse(
            {
                "erro": (
                    "O áudio foi enviado para o "
                    "Supabase, mas ocorreu um erro "
                    "ao salvar a música no Neon."
                ),
                "detalhes": str(e),
                "audio": url_publica
            },
            status=500
        )

    # ========================================================
    # RESPOSTA FINAL
    # ========================================================

    return JsonResponse(
        {
            "status": "sucesso",

            "mensagem": (
                "Áudio processado, convertido "
                "para MP3 e enviado ao Supabase."
            ),

            "id": musica.id,

            "titulo": musica.titulo,

            "videoId": musica.videoId,

            "cantor": musica.cantor,

            "audio": url_publica,

            "url": url_publica,

            "audio_url": url_publica
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

    video_id_validado = (
        validar_video_id(
            video_id
        )
    )

    if not video_id_validado:

        return JsonResponse(
            {
                "erro": (
                    "videoId inválido."
                )
            },
            status=400
        )

    video_id = video_id_validado

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

    video_id = validar_video_id(
        video_id
    )

    if not video_id:

        return JsonResponse(
            {
                "erro": (
                    "videoId inválido."
                )
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

