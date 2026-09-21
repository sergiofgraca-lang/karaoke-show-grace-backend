import json
import os
import re
import shutil
import subprocess
import unicodedata
import yt_dlp
import sys
import imageio_ffmpeg
from yt_dlp.globals import plugin_dirs
from yt_dlp.plugins import load_all_plugins
import requests
from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

def limpar_texto(texto):
    """
    Limpa e normaliza textos recebidos do YouTube.
    Mantém acentos e caracteres comuns, removendo
    espaços desnecessários e caracteres de controle.
    """

    if texto is None:
        return ""

    texto = str(texto)

    # Remove caracteres de controle
    texto = re.sub(r"[\x00-\x1f\x7f]", "", texto)

    # Normaliza espaços
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()

from .models import Musica

DIRETORIO_PLUGIN = os.path.dirname(os.path.dirname(__file__))

plugin_dirs.value = ["default", DIRETORIO_PLUGIN]

load_all_plugins()

print("🔌 Diretório de plugins yt-dlp:", DIRETORIO_PLUGIN)

from yt_dlp_plugins.extractor import getpot_bgutil
from yt_dlp_plugins.extractor import getpot_bgutil_http

print("🧪 PYTHON VERSÃO:", sys.version)
print("🧪 YT-DLP VERSÃO:", getattr(yt_dlp.version, "__version__", "desconhecida"))
print("🧪 BGUTIL HTTP CLASSE:", getpot_bgutil_http.BgUtilHTTPPTP)
print("🧪 BGUTIL HTTP PROVIDER:", getpot_bgutil_http.BgUtilHTTPPTP.PROVIDER_NAME)

try:
    from yt_dlp.extractor.youtube.pot import provider as pot_provider

    print(
        "🧪 PO TOKEN PROVIDERS:",
        list(pot_provider._pot_providers.value.keys())
    )

    print(
        "🧪 BGUTIL HTTP REGISTRADO:",
        "BgUtilHTTP" in pot_provider._pot_providers.value
    )

    print(
        "🧪 BGUTIL SCRIPT NODE REGISTRADO:",
        "BgUtilScriptNode" in pot_provider._pot_providers.value
    )

    print(
        "🧪 BGUTIL SCRIPT DENO REGISTRADO:",
        "BgUtilScriptDeno" in pot_provider._pot_providers.value
    )

except Exception as e:
    print("❌ ERRO AO LER PO TOKEN PROVIDERS:", repr(e))

print("🔌 Provider bgutil HTTP carregado explicitamente.")

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
def supabase_configurado():
    """
    Verifica se o Supabase está configurado corretamente.
    """

    return bool(
        SUPABASE_URL
        and SUPABASE_KEY
        and NOME_DO_BUCKET
    )




def eh_url_supabase(url):
    """
    Verifica se uma URL pertence ao Storage do Supabase.
    """
    if not url:
        return False

    url = str(url).strip()

    return (
        "supabase.co/storage/" in url
        or "/storage/v1/object/" in url
    )


def audio_supabase_existe(video_id):
    """
    Verifica se o arquivo MP3 existe no bucket privado do Supabase.
    """
    if not supabase_configurado():
        print("❌ Supabase não está configurado.")
        return False

    video_id = str(video_id).strip()

    if not video_id:
        return False

    nome_arquivo = f"{video_id}.mp3"

    url = (
        f"{SUPABASE_URL}/storage/v1/object/"
        f"{NOME_DO_BUCKET}/{nome_arquivo}"
    )

    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
    }

    try:
        resposta = requests.head(
            url,
            headers=headers,
            timeout=15,
        )

        print(
            "🔎 Verificação do áudio no Supabase:",
            resposta.status_code,
            nome_arquivo
        )

        if resposta.status_code == 200:
            return True

        # Alguns ambientes podem não aceitar HEAD.
        # Nesse caso fazemos uma consulta GET apenas para
        # confirmar a existência do arquivo.
        if resposta.status_code in (400, 405):
            resposta = requests.get(
                url,
                headers=headers,
                timeout=15,
                stream=True,
            )

            print(
                "🔎 Verificação GET do áudio:",
                resposta.status_code,
                nome_arquivo
            )

            return resposta.status_code == 200

        return False

    except Exception as e:
        print(
            "❌ Erro verificando áudio no Supabase:",
            repr(e)
        )
        return False

def gerar_url_assinada_supabase(video_id, segundos=3600):
    """
    Gera uma URL temporária para um arquivo privado
    armazenado no bucket do Supabase.
    """

    if not supabase_configurado():
        print("❌ Supabase não está configurado.")
        return None

    video_id = str(video_id).strip()

    if not video_id:
        print("❌ Video ID vazio.")
        return None

    nome_arquivo = f"{video_id}.mp3"

    url = (
        f"{SUPABASE_URL}/storage/v1/object/sign/"
        f"{NOME_DO_BUCKET}/{nome_arquivo}"
    )

    payload = {
        "expiresIn": segundos
    }

    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
    }

    try:
        resposta = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )

        print(
            "🔐 Supabase gerar URL assinada:",
            resposta.status_code
        )

        if resposta.status_code not in (200, 201):
            print(
                "❌ Erro ao gerar URL assinada:",
                resposta.text[:500]
            )
            return None

        dados = resposta.json()

        signed_url = (
            dados.get("signedURL")
            or dados.get("signedUrl")
            or dados.get("signed_url")
        )

        if not signed_url:
            print("❌ Supabase não retornou signedURL.")
            print("📦 Resposta:", dados)
            return None

        if signed_url.startswith("/"):
            signed_url = (
                f"{SUPABASE_URL}/storage/v1"
                f"{signed_url}"
            )

        elif signed_url.startswith("?"):
            signed_url = (
                f"{SUPABASE_URL}/storage/v1/object/sign/"
                f"{NOME_DO_BUCKET}/{nome_arquivo}"
                f"{signed_url}"
            )

        return signed_url

    except Exception as e:
        print(
            "❌ Erro ao gerar URL assinada:",
            repr(e)
        )
        return None




@csrf_exempt
def teste_bgutil(request):
    """
    Diagnóstico temporário:
    testa o yt-dlp na extração do YouTube,
    sem download, sem FFmpeg e sem Supabase.
    """

    import time
    import shutil
    import yt_dlp

    video_id = "8cr4wfJuTNw"
    url = f"https://www.youtube.com/watch?v={video_id}"

    inicio = time.perf_counter()

    resultado = {
        "video_id": video_id,
        "url": url,
        "etapa": "iniciando",
    }

    # Teste direto de conectividade com o bgutil Render
    resultado["teste_bgutil_ping"] = {
        "url": "https://bgutil-ytdlp-pot-provider-0f67.onrender.com/ping",
        "ok": False,
        "status": None,
        "resposta": "",
        "erro": "",
    }

    try:
        import requests

        resposta_ping = requests.get(
            "https://bgutil-ytdlp-pot-provider-0f67.onrender.com/ping",
            timeout=10,
        )

        resultado["teste_bgutil_ping"]["status"] = resposta_ping.status_code
        resultado["teste_bgutil_ping"]["resposta"] = resposta_ping.text[:1000]
        resultado["teste_bgutil_ping"]["ok"] = (
            resposta_ping.status_code == 200
        )

    except Exception as erro_ping:
        resultado["teste_bgutil_ping"]["erro"] = (
            f"{type(erro_ping).__name__}: {erro_ping}"
        )

    try:
        qjs_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "runtime",
            "qjs",
        )

        resultado["ambiente"] = {
            "python": os.sys.version,
            "yt_dlp": getattr(yt_dlp, "__version__", "desconhecido"),
            "node": shutil.which("node"),
            "deno": shutil.which("deno"),
            "qjs_path": qjs_path,
            "qjs_existe": os.path.exists(qjs_path),
            "qjs_executavel": os.access(qjs_path, os.X_OK),
        }


        resultado["runtime_candidatos"] = {
            caminho: {
                "existe": os.path.exists(caminho),
                "executavel": os.path.isfile(caminho) and os.access(caminho, os.X_OK),
            }
            for caminho in [
                "/usr/bin/node",
                "/usr/local/bin/node",
                "/opt/bin/node",
                "/var/task/node",
                "/var/task/nodejs/node",
                "/usr/bin/deno",
                "/usr/local/bin/deno",
                "/opt/bin/deno",
                "/var/task/deno",
                "/usr/bin/bun",
                "/usr/local/bin/bun",
                "/opt/bin/bun",
                "/var/task/bun",
                "/usr/bin/qjs",
                "/usr/local/bin/qjs",
                "/opt/bin/qjs",
            ]
        }

        # Teste real de execução do QuickJS
        resultado["teste_qjs_execucao"] = {
            "tentado": False,
            "ok": False,
            "saida": "",
            "erro": "",
        }

        if os.path.isfile(qjs_path) and os.access(qjs_path, os.X_OK):
            resultado["teste_qjs_execucao"]["tentado"] = True

            try:
                teste_qjs = subprocess.run(
                    [qjs_path, "-e", "print(1 + 2)"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                resultado["teste_qjs_execucao"]["ok"] = (
                    teste_qjs.returncode == 0
                    and teste_qjs.stdout.strip() == "3"
                )
                resultado["teste_qjs_execucao"]["saida"] = (
                    teste_qjs.stdout.strip()
                )
                resultado["teste_qjs_execucao"]["erro"] = (
                    teste_qjs.stderr.strip()
                )

            except Exception as erro_qjs:
                resultado["teste_qjs_execucao"]["erro"] = (
                    f"{type(erro_qjs).__name__}: {erro_qjs}"
                )

        resultado["etapa"] = "criando_youtube_dl"

        ydl_opts = {
            "quiet": False,
                "no_warnings": False,
                "nocheckcertificate": True,

                "fetch_pot": "always",

            "js_runtimes": {
                "quickjs": {
                    "path": qjs_path,
                }
            },

            "extractor_args": {
                "youtubepot-bgutilhttp": {
                    "base_url": (
                        "https://bgutil-ytdlp-pot-provider-0f67"
                        ".onrender.com"
                    )
                }
            },
        }

        resultado["ydl_opts"] = {
                "fetch_pot": "always",
            "js_runtimes": {
                "quickjs": {
                    "path": qjs_path,
                }
            },
            "bgutil_base_url": (
                "https://bgutil-ytdlp-pot-provider-0f67"
                ".onrender.com"
            ),
        }

        resultado["etapa"] = "extraindo_info"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                url,
                download=False,
            )

        formatos = info.get("formats") or []

        formatos_audio = []

        for formato in formatos:
            if formato.get("acodec") not in (None, "none"):
                formatos_audio.append({
                    "format_id": formato.get("format_id"),
                    "ext": formato.get("ext"),
                    "acodec": formato.get("acodec"),
                    "abr": formato.get("abr"),
                    "tbr": formato.get("tbr"),
                    "vcodec": formato.get("vcodec"),
                })

        resultado.update({
            "ok": True,
            "etapa": "extracao_concluida",
            "tempo_segundos": round(
                time.perf_counter() - inicio,
                3,
            ),
            "titulo": info.get("title"),
            "uploader": info.get("uploader"),
            "extractor": info.get("extractor"),
            "extractor_key": info.get("extractor_key"),
            "formatos_total": len(formatos),
            "formatos_audio": formatos_audio,
        })

    except Exception as e:

        resultado.update({
            "ok": False,
            "etapa": "erro_extracao",
            "tempo_segundos": round(
                time.perf_counter() - inicio,
                3,
            ),
            "erro_tipo": type(e).__name__,
            "erro": str(e),
        })

    return JsonResponse(resultado)

def validar_video_id(video_id):
    """
    Valida o ID de um vídeo do YouTube.
    IDs normais do YouTube possuem exatamente 11 caracteres.
    """

    if not video_id:
        return False

    video_id = str(video_id).strip()

    return bool(
        re.fullmatch(
            r"[A-Za-z0-9_-]{11}",
            video_id
        )
    )


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
    try:
        teste_bgutil = requests.get(
            "https://bgutil-ytdlp-pot-provider-0f67.onrender.com/ping",
            timeout=10
        )

        print(
            "🧪 TESTE BGUTIL PELO VERCEL:",
            teste_bgutil.status_code,
            teste_bgutil.text
        )

    except Exception as e:
        print(
            "❌ TESTE BGUTIL PELO VERCEL FALHOU:",
            str(e)
        )

    # ============================================================
    # 14. CONFIGURAÇÃO DO YT-DLP
    # ============================================================

    # ============================================================
    # QUICKJS
    # ============================================================

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

    if os.name == "nt":
        # Windows
        qjs_path = os.path.join(
            BASE_DIR,
            "runtime",
            "qjs-win",
            "qjs.exe"
        )
    else:
        # Linux / Vercel
        qjs_path = os.path.join(
            BASE_DIR,
            "runtime",
            "qjs"
        )

    print(
        "🧪 Sistema operacional:",
        os.name
    )

    print(
        "🧪 QJS configurado:",
        qjs_path
    )

    print(
        "🧪 QJS existe:",
        os.path.isfile(qjs_path)
    )

    ydl_opts = {
        "format": (
            "bestaudio/best"
        ),

        "outtmpl": os.path.join(
            pasta_temporaria,
            "%(id)s.%(ext)s"
        ),

        "noplaylist": True,

        "js_runtimes": (
            {
                "quickjs": {
                    "path": qjs_path
                }
            }
            if os.path.isfile(qjs_path)
            else {}
        ),

        "quiet": False,

        "no_warnings": False,

        "nocheckcertificate": True,

        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),

        "fetch_pot": "always",

    "extractor_args": {
        "youtubepot-bgutilhttp": {
            "base_url": "https://bgutil-ytdlp-pot-provider-0f67.onrender.com"
        }
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
        print("🧪 Node encontrado:", shutil.which("node"))
        print("🧪 Deno encontrado:", shutil.which("deno"))

        print("🧪 QJS configurado:", qjs_path)
        print("🧪 QJS existe:", os.path.isfile(qjs_path))

        print(
            "⬇️ Baixando áudio do YouTube..."
        )

        try:
            from yt_dlp.extractor.youtube.pot import provider as pot_provider

            providers_atuais = list(
                pot_provider._pot_providers.value.keys()
            )

            print(
                "🧪 PROVIDERS DENTRO DO DOWNLOAD:",
                providers_atuais
            )

        except Exception as e:

            print(
                "❌ ERRO AO LER PROVIDERS NO DOWNLOAD:",
                repr(e)
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
