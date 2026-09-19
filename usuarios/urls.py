from django.urls import path
from django.http import JsonResponse, HttpResponse
from .views import (
    processar_audio_youtube,
    listar_musicas,
    deletar_musica,
    ranking,
    listar_audios,
    associar_audio,
    audio_da_musica,
    servir_audio_supabase,  # RESTAURADO: Import da view de stream binário
    teste_bgutil,
    testar_youtube,
)

urlpatterns = [
    # Diagnóstico temporário Vercel
    path("teste-bgutil/", teste_bgutil),
    path("test-youtube/", testar_youtube),

    # Rota de Salvamento inicial (POST)
    path("salvar/", processar_audio_youtube),

    # Listagem e Gerenciamento
    path("listar/", listar_musicas),
    path("deletar/<int:id>/", deletar_musica),
    path("ranking/", ranking),
    path("audios/", listar_audios),
    path("associar-audio/", associar_audio),

    # Busca padrão textual da playlist (GET)
    path("audio/<str:video_id>/", audio_da_musica),

    # RESTAURADO: Mapeamento exato da rota que o front antigo em cache busca
    path("audio-arquivo/<str:video_id>/", servir_audio_supabase),
]
