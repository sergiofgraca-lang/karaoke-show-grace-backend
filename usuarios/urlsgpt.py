from django.urls import path

from .views import (
    associar_audio,
    audio_da_musica,
    deletar_musica,
    listar_audios,
    listar_musicas,
    processar_audio_youtube,  # <--- Nova função importada aqui
    ranking,
    salvar_musica,
)

urlpatterns = [
    path("salvar/", salvar_musica),
    path("listar/", listar_musicas),
    path("deletar/<int:id>/", deletar_musica),
    path("ranking/", ranking),
    path("audios/", listar_audios),
    path("associar-audio/", associar_audio),
    path("audio/<str:video_id>/", audio_da_musica),
    path(
        "download/", processar_audio_youtube
    ),  # <--- Nova rota para o React disparar
]