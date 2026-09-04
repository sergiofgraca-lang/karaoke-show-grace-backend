from django.urls import path
from .views import (
    processar_audio_youtube,  # Nossa view rápida e blindada
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
    
    # FORÇAR A ROTA QUE O SEU FRONTEND ANTIGO ESTÁ PROCURANDO:
    # Quando o React bater em /api/audio/ID/, o Django responde com a URL perfeita!
    path("audio/<str:video_id>/", processar_audio_youtube), 
]
