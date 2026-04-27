from django.urls import path
from .views import (
    salvar_musica,
    listar_musicas,
    deletar_musica,
    ranking,
    criar_admin
)

urlpatterns = [
    # 🎵 MÚSICAS
    path('salvar/', salvar_musica),
    path('listar/', listar_musicas),
    path('deletar/<int:id>/', deletar_musica),

    # 📊 RANKING
    path('ranking/', ranking),

    # 🔥 ADMIN TESTE
    path('criar-admin/', criar_admin),
]