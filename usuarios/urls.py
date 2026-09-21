Set-Content usuarios/urls.py -Value @"
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

# GATILHO COMPACTO DE QUEBRA DE CACHE DE ROTAS DA VERCEL - 2026
urlpatterns = [
    path("teste-bgutil/", teste_bgutil),
    path("test-youtube/", testar_youtube),
    path("salvar/", processar_audio_youtube),
    path("listar/", listar_musicas),
    path("deletar/<int:id>/", deletar_musica),
    path("ranking/", ranking),
    path("audios/", listar_audios),
    path("associar-audio/", associar_audio),
    
    # ROTAS DE COMPATIBILIDADE REATIVADAS PARA ANULAR O ERRO 404
    path("audio/<str:video_id>/", servir_audio_supabase),
    path("audio-arquivo/<str:video_id>/", servir_audio_supabase),
]
"@
