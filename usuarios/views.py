from django.http import JsonResponse
import json
from .models import Musica
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def salvar_musica(request):
    if request.method == "POST":
        data = json.loads(request.body)

        Musica.objects.create(
            titulo=data.get("titulo"),
            videoId=data.get("videoId"),
            cantor=data.get("cantor")
        )

        return JsonResponse({"status": "ok"})


def listar_musicas(request):
    musicas = Musica.objects.all().values()
    return JsonResponse(list(musicas), safe=False)