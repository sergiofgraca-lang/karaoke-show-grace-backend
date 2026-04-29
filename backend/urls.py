from django.contrib import admin
from django.urls import path, include  # ✅ AQUI ESTÁ O QUE FALTAVA

from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/', include('usuarios.urls')),

    # 🔥 LOGIN JWT
    path('api/token/', TokenObtainPairView.as_view()),
]