import json
import os
import re
import unicodedata

import yt_dlp

from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from supabase import create_client

from .models import Musica


# ============================================================
# SUPABASE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

supabase = None

if SUPABASE_URL and SUPABASE_SECRET_KEY:
    try:
        supabase = create_client(
            SUPABASE_URL,
            SUPABASE_SECRET_KEY
        )
    except Exception as e:
        print("❌ Erro ao conectar ao Supabase:", e)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def limpar_texto(texto):
    """
    Remove espaços extras e caracteres problemáticos.
    """
    if texto is None:
        return ""

    texto = str(texto).strip()

    texto = re.sub(r"\s+", " ", texto)

    return texto


def normalizar_texto(texto):
    """
    Normaliza texto para facilitar buscas.
    """
    if not texto:
        return ""

    texto = unicodedata.normalize(
        "NFD",
        str(texto)
    )

    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )

    return texto.lower().strip()


def encontrar_audio(video_id):
    """
    Procura um áudio local dentro de MEDIA_ROOT/audio.

    Retorna o caminho relativo:
        audio/nome.mp3

    ou None se não encontrar.
    """

    audio_dir = os.path.join(
        settings.MEDIA_ROOT,
        "audio"
    )

    if not os.path.exists(audio_dir):
        return None

    extensoes = [
        ".mp3",
        ".wav",
        ".ogg",
        ".m4a"
    ]

    video_id = str(video_id).strip()

    for arquivo in os.listdir(audio_dir):

        nome, extensao = os.path.splitext(arquivo)

        if extensao.lower() not in extensoes:
            continue

        if nome == video_id:
            return f"audio/{arquivo}"

    return None


# ============================================================
# TESTAR SUPABASE
# ============================================================

@csrf_exempt
def testar_supabase(request):

    if request.method != "GET":
        return JsonResponse(
            {
                "erro": "Método inválido. Use GET."
            },
            status=405
        )

    if not supabase:
        return JsonResponse(
            {
                "status": "erro",
                "mensagem": "Supabase não configurado."
            },
            status=500
        )

    return JsonResponse(
        {
            "status": "ok",
            "mensagem": "Supabase configurado corretamente."
        }
    )


# ============================================================
# SALVAR / PROCESSAR MÚSICA
# ============================================================

@csrf_exempt
def processar_audio_youtube(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "erro": "Método inválido. Use POST."
            },
            status=405
        )

    # --------------------------------------------------------
    # RECEBER DADOS
    # --------------------------------------------------------

    try:

        if request.content_type == "application/json":

            dados = json.loads(
                request.body
            )

            video_id = dados.get("videoId")
            titulo = dados.get("titulo")
            cantor = dados.get("cantor", "")

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
    # VALIDAR
    # --------------------------------------------------------

    video_id = limpar_texto(video_id)
    titulo = limpar_texto(titulo)
    cantor = limpar_texto(cantor)

    if not video_id:

        return JsonResponse(
            {
                "erro": "O campo videoId é obrigatório."
            },
            status=400
        )

    if not titulo:

        return JsonResponse(
            {
                "erro": "O campo titulo é obrigatório."
            },
            status=400
        )

    # --------------------------------------------------------
    # PROCURAR MÚSICA EXISTENTE
    # --------------------------------------------------------

    musica_existente = Musica.objects.filter(
        videoId=video_id
    ).first()

    if musica_existente:

        audio_existente = ""

        if musica_existente.audio:

            audio_existente = str(
                musica_existente.audio
            ).strip()

            # ------------------------------------------------
            # LIMPAR URLs FALSAS DO VEVIOZ
            # ------------------------------------------------

            if "vevioz.com" in audio_existente.lower():

                musica_existente.audio = ""

                musica_existente.save(
                    update_fields=["audio"]
                )

                audio_existente = ""

        return JsonResponse(
            {
                "status": "sucesso",
                "mensagem": "Música já cadastrada.",
                "id": musica_existente.id,
                "titulo": musica_existente.titulo,
                "videoId": musica_existente.videoId,
                "cantor": musica_existente.cantor,
                "audio_url": audio_existente
            },
            status=200
        )

    # --------------------------------------------------------
    # CRIAR NOVA MÚSICA
    #
    # IMPORTANTE:
    # NÃO colocar URL falsa aqui.
    # O áudio começa vazio.
    # --------------------------------------------------------

    try:

        nova_musica = Musica.objects.create(

            titulo=titulo,

            videoId=video_id,

            cantor=cantor,

            audio=""
        )

    except Exception as e:

        print(
            "❌ ERRO AO SALVAR MÚSICA:",
            e
        )

        return JsonResponse(
            {
                "erro": "Erro ao salvar música: " + str(e)
            },
            status=500
        )

    print(
        f"✅ Música criada: {nova_musica.id}"
    )

    print(
        f"🎵 Video ID: {video_id}"
    )

    print(
        "🔊 Áudio ainda não associado."
    )

    return JsonResponse(
        {
            "status": "sucesso",
            "mensagem": (
                "Música cadastrada. "
                "Áudio ainda não associado."
            ),
            "id": nova_musica.id,
            "titulo": nova_musica.titulo,
            "videoId": nova_musica.videoId,
            "cantor": nova_musica.cantor,
            "audio_url": ""
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
                "erro": "Método inválido. Use GET."
            },
            status=405
        )

    try:

        musicas = Musica.objects.all().order_by(
            "-id"
        )

        resultado = []

        for musica in musicas:

            audio = ""

            if musica.audio:

                audio = str(
                    musica.audio
                ).strip()

                # Nunca devolver URL falsa
                if "vevioz.com" in audio.lower():

                    audio = ""

            resultado.append(
                {
                    "id": musica.id,
                    "titulo": musica.titulo,
                    "videoId": musica.videoId,
                    "cantor": musica.cantor,
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
            e
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
def deletar_musica(request, id):

    if request.method != "DELETE":

        return JsonResponse(
            {
                "erro": "Método inválido. Use DELETE."
            },
            status=405
        )

    try:

        musica = Musica.objects.filter(
            id=id
        ).first()

        if not musica:

            return JsonResponse(
                {
                    "erro": "Música não encontrada."
                },
                status=404
            )

        musica.delete()

        return JsonResponse(
            {
                "status": "sucesso",
                "mensagem": "Música deletada."
            }
        )

    except Exception as e:

        print(
            "❌ ERRO AO DELETAR:",
            e
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
                "erro": "Método inválido. Use GET."
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
            list(ranking_musicas),
            safe=False
        )

    except Exception as e:

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
                "erro": "Método inválido. Use GET."
            },
            status=405
        )

    try:

        audio_dir = os.path.join(
            settings.MEDIA_ROOT,
            "audio"
        )

        if not os.path.exists(audio_dir):

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

        for arquivo in os.listdir(audio_dir):

            if os.path.splitext(
                arquivo
            )[1].lower() in extensoes:

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
                "erro": "Método inválido. Use POST."
            },
            status=405
        )

    try:

        if request.content_type == "application/json":

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

    video_id = limpar_texto(video_id)
    audio = limpar_texto(audio)

    if not video_id:

        return JsonResponse(
            {
                "erro": "videoId é obrigatório."
            },
            status=400
        )

    if not audio:

        return JsonResponse(
            {
                "erro": "audio é obrigatório."
            },
            status=400
        )

    # --------------------------------------------------------
    # IMPEDIR URL FALSA
    # --------------------------------------------------------

    if "vevioz.com" in audio.lower():

        return JsonResponse(
            {
                "erro": (
                    "URL de áudio inválida. "
                    "Vevioz não é uma fonte de áudio válida."
                )
            },
            status=400
        )

    try:

        musica = Musica.objects.filter(
            videoId=video_id
        ).first()

        if not musica:

            return JsonResponse(
                {
                    "erro": "Música não encontrada."
                },
                status=404
            )

        musica.audio = audio

        musica.save(
            update_fields=["audio"]
        )

        return JsonResponse(
            {
                "status": "sucesso",
                "mensagem": "Áudio associado com sucesso.",
                "videoId": musica.videoId,
                "audio": musica.audio
            }
        )

    except Exception as e:

        print(
            "❌ ERRO AO ASSOCIAR ÁUDIO:",
            e
        )

        return JsonResponse(
            {
                "erro": str(e)
            },
            status=500
        )


# ============================================================
# BUSCAR ÁUDIO DE UMA MÚSICA
# ============================================================

def audio_da_musica(request, video_id):

    if request.method != "GET":

        return JsonResponse(
            {
                "erro": "Método inválido. Use GET."
            },
            status=405
        )

    video_id = limpar_texto(video_id)

    print(
        "🔎 Procurando áudio associado ao videoId:",
        video_id
    )

    # --------------------------------------------------------
    # BUSCAR MÚSICA
    # --------------------------------------------------------

    try:

        musica = Musica.objects.filter(
            videoId=video_id
        ).first()

    except Exception as e:

        print(
            "❌ ERRO AO BUSCAR MÚSICA:",
            e
        )

        return JsonResponse(
            {
                "erro": str(e)
            },
            status=500
        )

    if not musica:

        return JsonResponse(
            {
                "erro": "Música não encontrada.",
                "videoId": video_id
            },
            status=404
        )

    # --------------------------------------------------------
    # PRIMEIRO: VERIFICAR ÁUDIO SALVO
    # --------------------------------------------------------

    if musica.audio:

        audio = str(
            musica.audio
        ).strip()

        # ----------------------------------------------------
        # LIMPAR URL FALSA DO VEVIOZ
        # ----------------------------------------------------

        if "vevioz.com" in audio.lower():

            print(
                "🧹 Removendo URL falsa do Vevioz."
            )

            musica.audio = ""

            musica.save(
                update_fields=["audio"]
            )

            audio = ""

        # ----------------------------------------------------
        # URL ABSOLUTA
        #
        # Supabase:
        # https://xxxxx.supabase.co/storage/v1/object/public/...
        #
        # NÃO adicionar MEDIA_URL.
        # ----------------------------------------------------

        elif audio.startswith(
            "http://"
        ) or audio.startswith(
            "https://"
        ):

            print(
                "✅ Áudio remoto encontrado:",
                audio
            )

            return JsonResponse(
                {
                    "status": "sucesso",
                    "titulo": musica.titulo,
                    "videoId": musica.videoId,
                    "audio": audio,
                    "url": audio
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

            audio = audio.lstrip("/")

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
                    "titulo": musica.titulo,
                    "videoId": musica.videoId,
                    "audio": url_audio,
                    "url": url_audio
                }
            )

    # --------------------------------------------------------
    # SEGUNDO: PROCURAR ARQUIVO LOCAL
    # --------------------------------------------------------

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
            update_fields=["audio"]
        )

        url_audio = (
            settings.MEDIA_URL
            + audio_local
        )

        return JsonResponse(
            {
                "status": "sucesso",
                "titulo": musica.titulo,
                "videoId": musica.videoId,
                "audio": url_audio,
                "url": url_audio
            }
        )

    # --------------------------------------------------------
    # NENHUM ÁUDIO
    # --------------------------------------------------------

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
            "titulo": musica.titulo,
            "videoId": musica.videoId,
            "audio": "",
            "url": ""
        },
        status=404
    )
