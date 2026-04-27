from django.http import JsonResponse
import json
from .models import Musica
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count
from django.contrib.auth.models import User


# 🔥 CRIAR ADMIN (TESTE)
def criar_admin(request):
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser(
            username="admin",
            password="123456"
        )
        return JsonResponse({"status": "admin criado"})

    return JsonResponse({"status": "já existe"})


# 🔥 RANKING
def ranking(request):
    dados = (
        Musica.objects
        .values('cantor')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    return JsonResponse(list(dados), safe=False)


# 🔥 SALVAR MÚSICA (CORRIGIDO E PROTEGIDO)
@csrf_exempt
def salvar_musica(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            Musica.objects.create(
                titulo=data.get("titulo"),
                videoId=data.get("videoId"),
                cantor=data.get("cantor")
            )

            return JsonResponse({"status": "ok"})

        except Exception as e:
            return JsonResponse({
                "status": "erro",
                "detalhe": str(e)
            })

    return JsonResponse({"status": "metodo invalido"})


# 🔥 LISTAR MÚSICAS
def listar_musicas(request):
    musicas = Musica.objects.all().values()
    return JsonResponse(list(musicas), safe=False)


# 🔥 DELETAR MÚSICA
@csrf_exempt
def deletar_musica(request, id):
    if request.method == "DELETE":
        try:
            musica = Musica.objects.get(id=id)
            musica.delete()
            return JsonResponse({"status": "ok"})
        except Musica.DoesNotExist:
            return JsonResponse({"status": "erro", "detalhe": "não encontrada"})
        except Exception as e:
            return JsonResponse({"status": "erro", "detalhe": str(e)})

    return JsonResponse({"status": "metodo invalido"})