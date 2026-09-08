from django.urls import path
from .views import (
    processar_audio_youtube,  # A sua view calibrada que aceita GET e POST
    listar_musicas,
    deletar_musica,
    ranking,
    listar_audios,
    associar_audio,
)

urlpatterns = [
    path("salvar/", processar_audio_youtube),
    path("listar/", listar_musicas),
    path("deletar/<int:id>/", deletar_musica),
    path("ranking/", ranking),
    path("audios/", listar_audios),
    path("associar-audio/", associar_audio),
    
    # 🎯 ESPELHAMENTO DA PLAYLIST ANTIGA:
    # Captura a busca em lote por ID e redireciona de forma limpa para a view do Supabase
    path("audio/<str:video_id>/", processar_audio_youtube),
]
