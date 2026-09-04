from django.urls import path
from .views import (
    processar_audio_youtube,  # Sua view unificada e rápida
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
    
    # 🎯 ESPELHAMENTO DE PRODUÇÃO:
    # O seu front antigo procura por "/api/audio/VIDEO_ID/". Forçamos o Django
    # a responder essa rota entregando a URL corrigida com as barras!
    path("audio/<str:video_id>/", processar_audio_youtube),
]
