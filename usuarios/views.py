import json
import os
import re
import unicodedata
import yt_dlp
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from supabase import create_client, Client
from .models import Musica

# CONFIGURAÇÃO SUPABASE STORAGE
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sua-chave-anon-public-do-supabase")
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
NOME_DO_BUCKET = "audio" # Crie um bucket chamado 'audio' no painel do seu Supabase Storage

def limpar_texto(texto):
    if not texto:
        return "Desconhecido"
    texto = (
        unicodedata.normalize("NFKD", str(texto))
        .encode("ascii", "ignore")
        .decode("utf-8")
    )
    return texto.strip()

@csrf_exempt
def processar_audio_youtube(request):
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido. Use POST."}, status=405)

    if request.content_type == "application/json":
        try:
            dados = json.loads(request.body)
            video_id = dados.get("videoId")
            titulo = dados.get("titulo")
            cantor = dados.get("cantor", "")
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido."}, status=400)
    else:
        video_id = request.POST.get("videoId")
        titulo = request.POST.get("titulo")
        cantor = request.POST.get("cantor", "")

    if not video_id or not titulo:
        return JsonResponse({"erro": "Os campos videoId e titulo são obrigatórios."}, status=400)

    titulo_limpo = limpar_texto(titulo)
    cantor_limpo = limpar_texto(cantor)

    # 1. VERIFICAÇÃO DE DUPLICIDADE
    musica_existente = Musica.objects.filter(videoId=video_id).first()
    if musica_existente:
        return JsonResponse({
            "status": "sucesso",
            "id": musica_existente.id,
            "titulo": musica_existente.titulo,
            "videoId": musica_existente.videoId,
            "cantor": musica_existente.cantor,
            "audio_url": str(musica_existente.audio)
        })

    # 2. CAPTURAR FLUXO DE ÁUDIO REAL VIA YT-DLP (SEM SALVAR EM DISCO NA VERCEL)
    url_audio_final = ""
    nome_arquivo_supabase = f"{video_id}.mp3"
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    try:
        url_youtube = f"https://youtube.com{video_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_youtube, download=False)
            stream_url = info.get('url', '')
            
            if stream_url:
                # Baixamos o pedaço do fluxo de áudio diretamente na memória RAM da Vercel
                resposta_stream = requests.get(stream_url, stream=True, timeout=10)
                conteudo_audio = resposta_stream.content
                
                # Enviamos o arquivo binário bruto diretamente para o Supabase Storage (Bucket 'audio')
                supabase_client.storage.from_(NOME_DO_BUCKET).upload(
                    path=nome_arquivo_supabase,
                    file=conteudo_audio,
                    file_options={"content-type": "audio/mp3"}
                )
                
                # Montamos a URL pública permanente gerada pelo próprio Supabase
                url_audio_final = f"{SUPABASE_URL}/storage/v1/object/public/{NOME_DO_BUCKET}/{nome_arquivo_supabase}"
                
    except Exception as e:
        print(f"⚠️ Falha no upload para o Supabase Storage: {str(e)}")

    # Fallback de segurança se o Storage falhar
    if not url_audio_final:
        url_audio_final = f"https://vevioz.com{video_id}"

    # 3. SALVAR REGISTRO NO BANCO POSTGRESQL DA SUPABASE
    try:
        nova_musica = Musica.objects.create(
            titulo=titulo_limpo,
            videoId=video_id,
            cantor=cantor_limpo,
            audio=url_audio_final,
        )
    except Exception as e:
        return JsonResponse({"erro": f"Erro na Supabase: {str(e)}"}, status=500)

    return JsonResponse({
        "status": "sucesso",
        "id": nova_musica.id,
        "titulo": nova_musica.titulo,
        "videoId": nova_musica.videoId,
        "cantor": nova_musica.cantor,
        "audio_url": nova_musica.audio,
    }, status=201)



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

        for arquivo in os.listdir(
            audio_dir
        ):

            extensao = os.path.splitext(
                arquivo
            )[1].lower()

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

    # --------------------------------------------------------
    # RECEBER DADOS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # LIMPAR
    # --------------------------------------------------------

    video_id = limpar_texto(
        video_id
    )

    audio = limpar_texto(
        audio
    )

    # --------------------------------------------------------
    # VALIDAR
    # --------------------------------------------------------

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
    # IMPEDIR VEVIOZ
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

    # --------------------------------------------------------
    # LOCALIZAR MÚSICA
    # --------------------------------------------------------

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

        print(
            "✅ Áudio associado:",
            audio
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

def encontrar_audio(video_id):
    raise NotImplementedError


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

    video_id = limpar_texto(
        video_id
    )

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
    # VERIFICAR ÁUDIO SALVO
    # --------------------------------------------------------

    if musica.audio:

        audio = str(
            musica.audio
        ).strip()

        # ----------------------------------------------------
        # URL FALSA DO VEVIOZ
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
        # Exemplo Supabase:
        #
        # https://xxxxx.supabase.co/storage/...
        #
        # NÃO adicionar MEDIA_URL.
        # ----------------------------------------------------

        elif (
            audio.startswith("http://")
            or
            audio.startswith("https://")
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

            audio = audio.lstrip(
                "/"
            )

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
    # PROCURAR ÁUDIO LOCAL
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
    # NENHUM ÁUDIO REAL
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
