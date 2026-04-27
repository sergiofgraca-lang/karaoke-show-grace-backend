from django.http import JsonResponse
import json
from .models import Musica
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from .models import Musica

def ranking(request):
    dados = (
        Musica.objects
        .values('cantor')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    return JsonResponse(list(dados), safe=False)

@csrf_exempt
def deletar_musica(request, id):
    if request.method == "DELETE":
        from .models import Musica

        try:
            musica = Musica.objects.get(id=id)
            musica.delete()
            return JsonResponse({"status": "ok"})
        except:
            return JsonResponse({"status": "erro"})

def login(request):
    if request.method == "POST":
        data = json.loads(request.body)

        usuario = data.get("usuario")
        senha = data.get("senha")

        if usuario == "Sirgio" and senha == "Sirgiograce@1":
            return JsonResponse({"status": "ok"})
        else:
            return JsonResponse({"status": "erro"})

    return JsonResponse({"status": "ok"})

def salvar_musica(request):
    if request.method == "POST":
        data = json.loads(request.body)

        musica = Musica.objects.create(
            titulo=data.get("titulo"),
            videoId=data.get("videoId"),
            cantor=data.get("cantor")
        )

        return JsonResponse({"status": "ok"})
        

def listar_musicas(request):
    musicas = Musica.objects.all().values()

    return JsonResponse(list(musicas), safe=False)