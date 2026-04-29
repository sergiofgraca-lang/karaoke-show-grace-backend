from django.urls import path
from .views import salvar_musica, listar_musicas

urlpatterns = [
    path("salvar/", salvar_musica),
    path("listar/", listar_musicas),
]