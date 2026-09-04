import os 
import json
import re
import unicodedata
from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Musica  # Garanta que o seu import está correto

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
# PROCESSAR ÁUDIO DO YOUTUBE (VERSÃO ULTRA-LEVE PARA VERCEL)
# =========================================================
@csrf_exempt
def processar_audio_youtube(request):

    # 1. VALIDAR MÉTODO
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido. Use POST."}, status=405)

    # 2. CAPTURAR DADOS
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

    # 3. VALIDAR CAMPOS
    if not video_id or not titulo:
        return JsonResponse({"erro": "Os campos videoId e titulo são obrigatórios."}, status=400)

    titulo_limpo = limpar_texto(titulo)
    cantor_limpo = limpar_texto(cantor)

    # 4. VERIFICAÇÃO DE DUPLICIDADE NO BANCO DA SUPABASE
    musica_existente = Musica.objects.filter(videoId=video_id).first()

    if musica_existente:
        return JsonResponse(
            {
                "status": "sucesso",
                "mensagem": "Música já processada anteriormente.",
                "id": musica_existente.id,
                "titulo": musica_existente.titulo,
                "videoId": musica_existente.videoId,
                "cantor": musica_existente.cantor,
                "audio_url": str(musica_existente.audio),
            }
        )

    # 5. ASSOCIAÇÃO DA URL EXTERNA DE STREAM (Livre de downloads e pastas)
    audio_registrado = f"https://vevioz.com{video_id}"

    # 6. SALVAR REGISTRO NO BANCO POSTGRESQL DA SUPABASE
    try:
        nova_musica = Musica.objects.create(
            titulo=titulo_limpo,
            videoId=video_id,
            cantor=cantor_limpo,
            audio=audio_registrado,
        )
    except Exception as e:
        return JsonResponse({"erro": f"Erro na Supabase: {str(e)}"}, status=500)

    # 7. RETORNAR SUCESSO INSTANTÂNEO PARA O REACT
    return JsonResponse(
        {
            "status": "sucesso",
            "mensagem": "Música salva com áudio associado com sucesso.",
            "id": nova_musica.id,
            "titulo": nova_musica.titulo,
            "videoId": nova_musica.videoId,
            "cantor": nova_musica.cantor,
            "audio_url": nova_musica.audio,
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
# PROCESSAR ÁUDIO DO YOUTUBE (ADAPTADO PARA VERCEL SERVERLESS)
# =========================================================
@csrf_exempt
def processar_audio_youtube(request):

    # -----------------------------------------------------
    # 1. VALIDAR MÉTODO
    # -----------------------------------------------------
    if request.method != "POST":
        return JsonResponse({"erro": "Método inválido. Use POST."}, status=405)

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
            return JsonResponse({"erro": "JSON inválido."}, status=400)
    else:
        video_id = request.POST.get("videoId")
        titulo = request.POST.get("titulo")
        cantor = request.POST.get("cantor", "")

    # -----------------------------------------------------
    # 3. VALIDAR CAMPOS
    # -----------------------------------------------------
    if not video_id or not titulo:
        return JsonResponse({"erro": "Os campos videoId e titulo são obrigatórios."}, status=400)

    titulo_limpo = limpar_texto(titulo)
    cantor_limpo = limpar_texto(cantor)

    # -----------------------------------------------------
    # 4. VERIFICAR DUPLICIDADE NO BANCO DA SUPABASE
    # -----------------------------------------------------
    musica_existente = Musica.objects.filter(videoId=video_id).first()

    if musica_existente:
        # Se for um FileField local do localhost antigo, adiciona o MEDIA_URL,
        # caso contrário retorna a URL string direta salva da API
        if musica_existente.audio and not str(musica_existente.audio).startswith("http"):
            audio_existente = settings.MEDIA_URL + str(musica_existente.audio)
        else:
            audio_existente = str(musica_existente.audio) if musica_existente.audio else ""

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
    # 5. GERAR URL DO STREAM MP3 VIA API EXTERNA (EVITA TIMEOUT NA VERCEL)
    # -----------------------------------------------------
    # Removemos os blocos do yt-dlp e do ffmpeg locais que quebravam em ambiente serverless.
    # Esta API pública gera o arquivo binário direto do fluxo do YouTube dinamicamente.
    audio_registrado = f"https://vevioz.com{video_id}"

    # -----------------------------------------------------
    # 6. SALVAR NO BANCO POSTGRESQL DA SUPABASE
    # -----------------------------------------------------
    try:
        nova_musica = Musica.objects.create(
            titulo=titulo_limpo,
            videoId=video_id,
            cantor=cantor_limpo,
            audio=audio_registrado, # Salva a URL externa diretamente no campo
        )

    except Exception as e:
        print("❌ ERRO AO SALVAR MÚSICA NA SUPABASE:")
        print(str(e))
        return JsonResponse({"erro": f"Erro ao salvar música: {str(e)}"}, status=500)

    # -----------------------------------------------------
    # 7. RETORNAR SUCESSO PARA O REACT (TONE.JS)
    # -----------------------------------------------------
    return JsonResponse(
        {
            "status": "sucesso",
            "mensagem": "Música salva com áudio associado com sucesso.",
            "id": nova_musica.id,
            "titulo": nova_musica.titulo,
            "videoId": nova_musica.videoId,
            "cantor": nova_musica.cantor,
            "audio_url": nova_musica.audio,
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