from django.urls import path
from django.http import JsonResponse, HttpResponse
from .views import (
    processar_audio_youtube,
    listar_musicas,
    deletar_musica,
    ranking,
    listar_audios,
    associar_audio,
    audio_da_musica,  # A view estável que entrega a URL em texto
    teste_bgutil,
    testar_youtube,
)

urlpatterns = [
    # Diagnóstico temporário Vercel
    path("teste-bgutil/", teste_bgutil),
    path("test-youtube/", testar_youtube),

    # Rota de Salvamento inicial (POST)
    path("salvar/", processar_audio_youtube),

    # Rotas de gerenciamento internas
    path("listar/", listar_musicas),
    path("deletar/<int:id>/", deletar_musica),
    path("ranking/", ranking),
    path("audios/", listar_audios),
    path("associar-audio/", associar_audio),

    # Busca padrão da playlist
    path("audio/<str:video_id>/", audio_da_musica),

    # =========================================================================
    # A JOGADA MÁGICA CONTRA O CACHE DO FRONTEND:
    # Mapeamos a rota de arquivo travada no front antigo para apontar para a nossa 
    # view textual estável. Isso anula o loop infinito e entrega a CDN do Supabase!
    # =========================================================================
    path("audio-arquivo/<str:video_id>/", audio_da_musica),
]
