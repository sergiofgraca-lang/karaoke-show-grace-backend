from django.urls import path

from .views import salvar_musica
from .views import salvar_musica, listar_musicas
from .views import deletar_musica
from .views import ranking

urlpatterns = [
   
    path('salvar/', salvar_musica),
    path('listar/', listar_musicas),
    path('deletar/<int:id>/', deletar_musica),
    path('ranking/', ranking),
]