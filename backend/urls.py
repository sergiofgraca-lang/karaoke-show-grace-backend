from django.contrib import admin
from django.urls import path, include

# 🔥 JWT LOGIN
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # suas APIs
    path('api/', include('usuarios.urls')),

    # 🔥 LOGIN JWT (FALTAVA ISSO)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]