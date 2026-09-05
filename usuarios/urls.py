from django.urls import path

from .views import (
    processar_audio_youtube,
    listar_musicas,
    deletar_musica,
    ranking,
    listar_audios,
    associar_audio,
    audio_da_musica,
)

urlpatterns = [
    # Salvar/processar uma música
    path("salvar/", processar_audio_youtube),

    # Processar explicitamente o áudio do YouTube
    path("processar-audio/", processar_audio_youtube),

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

    # Consultar o áudio real de uma música
    path("audio/<str:video_id>/", audio_da_musica),
]