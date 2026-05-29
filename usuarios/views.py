from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
import json

from .models import Musica


@csrf_exempt
def salvar_musica(request):

    if request.method == "GET":
        return JsonResponse(
            {"mensagem": "Use POST para salvar música"},
            status=200
        )

    if request.method == "POST":
        try:
            body = request.body.decode("utf-8")

            data = json.loads(body) if body else {}

            Musica.objects.create(
                titulo=data.get("titulo", ""),
                videoId=data.get("videoId", ""),
                cantor=data.get("cantor", ""),
            )

            return JsonResponse(
                {"status": "ok"},
                status=201
            )

        except Exception as e:
            print("ERRO SALVAR:", str(e))

            return JsonResponse(
                {"erro": str(e)},
                status=500
            )

    return JsonResponse(
        {"erro": "Método não permitido"},
        status=405
    )


def listar_musicas(request):
    musicas = list(
        Musica.objects.all().values()
    )

    return JsonResponse(
        musicas,
        safe=False
    )


@csrf_exempt
def deletar_musica(request, id):
    try:
        musica = Musica.objects.get(id=id)
        musica.delete()

        return JsonResponse({"status": "ok"})

    except Musica.DoesNotExist:
        return JsonResponse(
            {"erro": "não encontrada"},
            status=404
        )


def ranking(request):
    dados = (
        Musica.objects
        .values("cantor")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    return JsonResponse(
        list(dados),
        safe=False
    )