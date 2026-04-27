from django.urls import path

from .views import salvar_musica
from .views import salvar_musica, listar_musicas
from .views import deletar_musica
from .views import ranking
from django.contrib import admin
from django.urls import path, include
from .views import criar_admin

urlpatterns = [
    path('admin/', admin.site.urls),  # 👈 ESSENCIAL
    path('api/', include('usuarios.urls')),
    path('criar-admin/', criar_admin),
]

urlpatterns = [
   
    path('salvar/', salvar_musica),
    path('listar/', listar_musicas),
    path('deletar/<int:id>/', deletar_musica),
    path('ranking/', ranking),
]