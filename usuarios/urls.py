from django.urls import path
from .views import salvar_musica, listar_musicas, deletar_musica, ranking, criar_admin

urlpatterns = [
    path('salvar/', salvar_musica),
    path('listar/', listar_musicas),
    path('deletar/<int:id>/', deletar_musica),
    path('ranking/', ranking),

    # 🔥 TEMPORÁRIO
    path('criar-admin/', criar_admin),
]