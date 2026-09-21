import json
import os
import re
import unicodedata
import yt_dlp
import requests
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Musica

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SECRET_KEY")
NOME_DO_BUCKET = "audios"

def limpar_texto(texto):
    if not texto: return "Desconhecido"
    return str(texto).strip()

@csrf_exempt
def processar_audio_youtube(request, video_id=None):
    if request.method not in ["POST", "GET"]:
        return JsonResponse({"erro": "Método inválido."}, status=405)
    if not video_id:
        if request.content_type == "application/json":
            try: dados = json.loads(request.body); video_id = dados.get("videoId")
            except: return JsonResponse({"erro": "JSON inválido."}, status=400)
        else: video_id = request.POST.get("videoId")
    url_proxy = f"https://karaoke-show-grace-backend.vercel.app/api/audio-arquivo/{video_id}/"
    return JsonResponse({"status": "sucesso", "audio": url_proxy, "url": url_proxy, "audio_url": url_proxy})

@csrf_exempt
def servir_audio_supabase(request, video_id):
    """
    TÚNEL BINÁRIO EXPRESSO ANTI-TIMEOUT: Puxa o áudio original e entrega uma resposta
    binária estática instantânea para o Tone.js destravar o buffer sem estourar limites da Vercel.
    """
    video_id = str(video_id).strip()
    url_fonte = f"https://vevioz.com{video_id}"
    try:
        # Faz uma requisição GET rápida limitando o download para os primeiros 3MB para evitar timeout
        headers = {"Range": "bytes=0-3000000"}
        resposta_fonte = requests.get(url_fonte, headers=headers, timeout=8)
        resposta = HttpResponse(resposta_fonte.content, content_type="audio/mp3")
        resposta["Access-Control-Allow-Origin"] = "*"
        resposta["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
        resposta["Access-Control-Allow-Headers"] = "*"
        return resposta
    except Exception as e:
        return HttpResponse(b"", content_type="audio/mp3", status=404)

@csrf_exempt
def audio_da_musica(request, video_id):
    url_proxy = f"https://karaoke-show-grace-backend.vercel.app/api/audio-arquivo/{video_id}/"
    return JsonResponse({"status": "sucesso", "audio": url_proxy, "url": url_proxy, "audio_url": url_proxy})

@csrf_exempt
def listar_musicas(request): return JsonResponse([], safe=False)
@csrf_exempt
def deletar_musica(request, id): return JsonResponse({"status": "sucesso"})
@csrf_exempt
def ranking(request): return JsonResponse([], safe=False)
@csrf_exempt
def listar_audios(request): return JsonResponse({"status": "Disponivel"})
@csrf_exempt
def associar_audio(request): return JsonResponse({"status": "Sucesso"})
