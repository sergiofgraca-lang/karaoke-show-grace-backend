from django.http import JsonResponse
import json

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