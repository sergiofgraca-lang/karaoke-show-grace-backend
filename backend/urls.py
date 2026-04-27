from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from rest_framework_simplejwt.views import TokenObtainPairView


def home(request):
    return HttpResponse("API ONLINE 🚀")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('usuarios.urls')),
    path('', home),
    path('api/token/', TokenObtainPairView.as_view()),
]