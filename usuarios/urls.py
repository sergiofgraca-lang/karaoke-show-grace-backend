from django.urls import path

from .views import (
    associar_audio,
    audio_da_musica,
    deletar_musica,
    listar_audios,
    listar_musicas,
    processar_audio_youtube,  # <--- Mudamos aqui para o nome novo da sua view
    ranking,
    testar_supabase,
)

urlpatterns = [
    # Mapeia a rota antiga "salvar/" diretamente para a nova lógica da view
    path("salvar/", processar_audio_youtube),
    path("listar/", listar_musicas),
    path("deletar/<int:id>/", deletar_musica),
    path("ranking/", ranking),
    path("audios/", listar_audios),
    path("associar-audio/", associar_audio),
    path("audio/<str:video_id>/", audio_da_musica),
    path("testar-supabase/", testar_supabase),
]
