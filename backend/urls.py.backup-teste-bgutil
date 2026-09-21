
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


def home(request):
    return HttpResponse("API Karaoke funcionando 🚀")


urlpatterns = [
    path("", home),

    path("admin/", admin.site.urls),

    # Rotas do aplicativo usuarios
    path("api/", include("usuarios.urls")),

    # JWT - Login
    path(
        "api/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    # JWT - Renovar token
    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
]


# ==========================================
# ARQUIVOS DE MÍDIA - DESENVOLVIMENTO
# ==========================================

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

