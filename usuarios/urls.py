from django.urls import path
from django.http import JsonResponse, HttpResponse
from .views import (
    processar_audio_youtube,  # Nossa view unificada e protegida contra bots
    listar_musicas,
    deletar_musica,
    ranking,
    listar_audios,
    associar_audio,
    servir_audio_supabase,
    teste_bgutil,
    testar_youtube,
)

urlpatterns = [
    # Diagnóstico temporário Vercel -> Render/bgutil
    path("teste-bgutil/", teste_bgutil),

    # Diagnóstico temporário Vercel -> YouTube
    path("test-youtube/", testar_youtube),

    # Salvar/processar uma música (POST)
    path("salvar/", processar_audio_youtube),

    # Listagem
    path("listar/", listar_musicas),

    # Exclusão
    path("deletar/<int:id>/", deletar_musica),

    # Ranking
    path("ranking/", ranking),

    # Áudios disponíveis
    path("audios/", listar_audios),

    # Associar áudio manualmente
    path("associar-audio/", associar_audio),

    # CORREÇÃO CHAVE: Aponta as consultas da playlist para a nossa view blindada de produção (GET)
    path("audio/<str:video_id>/", processar_audio_youtube),

    # Entregar o MP3 privado do Supabase através do Django
    path("audio-arquivo/<str:video_id>/", servir_audio_supabase),
]
