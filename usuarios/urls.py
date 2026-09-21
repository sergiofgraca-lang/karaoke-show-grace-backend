from django.urls import path
from .views import (
    processar_audio_youtube,
    listar_musicas,
    deletar_musica,
    ranking,
    listar_audios,
    associar_audio,
    servir_audio_supabase,
    teste_bgutil,
    testar_youtube,
)

# =========================================================================
# CONFIGURAÇÃO DE ROTAS BLINDADAS CONTRA ERRO 404 E CACHE
# =========================================================================
urlpatterns = [
    path("teste-bgutil/", teste_bgutil),
    path("test-youtube/", testar_youtube),
    
    # Rota de Salvamento inicial expresso (POST)
    path("salvar/", processar_audio_youtube),
    
    # Gerenciamento do Painel e Playlist
    path("listar/", listar_musicas),
    path("deletar/<int:id>/", deletar_musica),
    path("ranking/", ranking),
    path("audios/", listar_audios),
    path("associar-audio/", associar_audio),
    
    # ROTAS DE COMPATIBILIDADE REATIVADAS (ENTREGAM O ÁUDIO CHUNKS PRO FRONT CACHEADO)
    path("audio/<str:video_id>/", servir_audio_supabase),
    path("audio-arquivo/<str:video_id>/", servir_audio_supabase),
]
