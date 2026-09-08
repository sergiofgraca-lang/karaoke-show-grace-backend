import json
import os
import re
import unicodedata
import yt_dlp
import requests
from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
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


def audio_supabase_existe(video_id):
    """
    Verifica via requisição HTTP rápida se o arquivo já está disponível no Storage públicos.
    Resolve o erro da linha 896.
    """
    if not video_id:
        return False
    # Constrói o link direto usando as variáveis de escopo já definidas no arquivo
    url_publica = f"{SUPABASE_URL}/storage/v1/object/public/{NOME_DO_BUCKET}/{video_id}.mp3"
    try:
        # Faz um 'HEAD' que apenas checa a existência do arquivo sem baixá-lo (super rápido)
        resposta = requests.head(url_publica, timeout=5)
        return resposta.status_code == 200
    except Exception:
        return False

# =========================================================================

@csrf_exempt
def processar_audio_youtube(request, video_id=None):
    # 1. Permite tanto POST (para buscas novas) quanto GET (para carregar da playlist)
    if request.method not in ["POST", "GET"]:
        return JsonResponse({"erro": "Método inválido. Use POST ou GET."}, status=405)

    # 2. Se o video_id não veio por parâmetro na URL, tenta capturar do corpo da requisição (POST)
    if not video_id:
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
    else:
        # Se veio via GET da playlist, capturamos os dados textuais complementares opcionais
        titulo = request.GET.get("titulo", "Karaoke")
        cantor = request.GET.get("cantor", "")

    if not video_id:
        return JsonResponse({"erro": "O campo videoId é obrigatório."}, status=400)

    # ... O restante do código de upload pro Supabase Storage e gravação no Neon continua igual embaixo ...


    titulo_limpo = limpar_texto(titulo)
    cantor_limpo = limpar_texto(cantor)

    # URL permanente que este arquivo receberá no seu Supabase Storage
    nome_arquivo = f"{video_id}.mp3"
    url_supabase_obrigatoria = f"{SUPABASE_URL}/storage/v1/object/public/{NOME_DO_BUCKET}/{nome_arquivo}"

    # 1. VERIFICAÇÃO DE DUPLICIDADE (IGNORA LINKS QUEBRADOS ANTIGOS)
    musica_existente = Musica.objects.filter(videoId=video_id).first()
    if musica_existente:
        # Se o link guardado no Neon for do vevioz ou antigo local, atualiza para o Supabase
        if "vevioz" in str(musica_existente.audio) or not str(musica_existente.audio).startswith("http"):
            musica_existente.audio = url_supabase_obrigatoria
            musica_existente.save()

        return JsonResponse({
            "status": "sucesso",
            "id": musica_existente.id,
            "titulo": musica_existente.titulo,
            "videoId": musica_existente.videoId,
            "cantor": musica_existente.cantor,
            "audio": url_supabase_obrigatoria,
            "url": url_supabase_obrigatoria,
            "audio_url": url_supabase_obrigatoria
        })

    # 2. SE FOR UMA MÚSICA INÉDITA, BAIXA EM MEMÓRIA E ENVIA PRO BUCKET
    url_audio_final = url_supabase_obrigatoria
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
                # Transfere o fluxo de áudio diretamente para a memória RAM
                resposta_stream = requests.get(stream_url, stream=True, timeout=15)
                
                # Endpoint REST oficial do Supabase Storage
                url_upload_supabase = f"{SUPABASE_URL}/storage/v1/object/{NOME_DO_BUCKET}/{nome_arquivo}"
                headers_supabase = {
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "audio/mp3"
                }
                
                upload_req = requests.post(url_upload_supabase, headers=headers_supabase, data=resposta_stream.content, timeout=20)
                
                # Validação matemática limpa (Status 300 ou maior é erro de envio)
                if upload_req.status_code >= 300:
                    print(f"⚠️ Erro no Storage HTTP: {upload_req.status_code}")
                    url_audio_final = ""
    except Exception as e:
        print(f"⚠️ Erro geral no processamento de mídia: {str(e)}")
        url_audio_final = ""

    # Fallback seguro (Sua engrenagem nunca para caso o Supabase falhe)
    if not url_audio_final:
        url_audio_final = f"https://vevioz.com{video_id}"

    # 3. GRAVA NO SEU BANCO DE DADOS (NEON)
    try:
        nova_musica = Musica.objects.create(
            titulo=titulo_limpo,
            videoId=video_id,
            cantor=cantor_limpo,
            audio=url_audio_final,
        )
    except Exception as e:
        return JsonResponse({"erro": f"Erro no Neon: {str(e)}"}, status=500)

    return JsonResponse({
        "status": "sucesso",
        "id": nova_musica.id,
        "titulo": nova_musica.titulo,
        "videoId": nova_musica.videoId,
        "cantor": nova_musica.cantor,
        "audio": url_audio_final,
        "url": url_audio_final,
        "audio_url": url_audio_final
    }, status=201)



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

