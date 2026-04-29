from django.http import JsonResponse
import json
from .models import Musica
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count


# 🔥 SALVAR
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


# 🔥 LISTAR
def listar_musicas(request):
    musicas = Musica.objects.all().values()
    return JsonResponse(list(musicas), safe=False)


# 🔥 DELETAR
def deletar_musica(request, id):
    try:
        musica = Musica.objects.get(id=id)
        musica.delete()
        return JsonResponse({"status": "ok"})
    except Musica.DoesNotExist:
        return JsonResponse({"erro": "não encontrada"}, status=404)


# 🔥 RANKING (AGRUPADO POR CANTOR)
def ranking(request):
    ranking = (
        Musica.objects
        .values("cantor")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    return JsonResponse(list(ranking), safe=False)