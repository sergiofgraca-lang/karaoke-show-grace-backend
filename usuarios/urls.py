from django.urls import path
from .views import (
    processar_audio_youtube,
    listar_musicas,
    deletar_musica,
    ranking,
    listar_audios,
    associar_audio,
    servir_audio_supabase,  # O executor estável do túnel fatiado
    teste_bgutil,
    testar_youtube,
)

urlpatterns = [
    # Diagnósticos auxiliares
    path("teste-bgutil/", teste_bgutil),
    path("test-youtube/", testar_youtube),

    # Rota de Salvamento inicial expresso (POST)
    path("salvar/", processar_audio_youtube),

    # Listagem e Gerenciamento Relacional
    path("listar/", listar_musicas),
    path("deletar/<int:id>/", deletar_musica),
    path("ranking/", ranking),
    path("audios/", listar_audios),
    path("associar-audio/", associar_audio),

    # 🎯 COMPATIBILIDADE DE CACHE (GATILHO CHAVE):
    # Faz com que todas as rotas antigas consultadas pelo front cacheado
    # caiam direto no nosso executor de áudio em chunks anti-timeout!
    path("audio/<str:video_id>/", servir_audio_supabase),
    path("audio-arquivo/<str:video_id>/", servir_audio_supabase),
]
