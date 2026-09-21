from pathlib import Path

arquivo = Path(r".\usuarios\views.py")
texto = arquivo.read_text(encoding="utf-8")

alvo = '''    resultado = {
        "video_id": video_id,
        "url": url,
        "etapa": "iniciando",
    }
'''

novo = '''    resultado = {
        "video_id": video_id,
        "url": url,
        "etapa": "iniciando",
    }

    # Teste direto de conectividade com o bgutil Render
    resultado["teste_bgutil_ping"] = {
        "url": "https://bgutil-ytdlp-pot-provider-0f67.onrender.com/ping",
        "ok": False,
        "status": None,
        "resposta": "",
        "erro": "",
    }

    try:
        import requests

        resposta_ping = requests.get(
            "https://bgutil-ytdlp-pot-provider-0f67.onrender.com/ping",
            timeout=10,
        )

        resultado["teste_bgutil_ping"]["status"] = resposta_ping.status_code
        resultado["teste_bgutil_ping"]["resposta"] = resposta_ping.text[:1000]
        resultado["teste_bgutil_ping"]["ok"] = (
            resposta_ping.status_code == 200
        )

    except Exception as erro_ping:
        resultado["teste_bgutil_ping"]["erro"] = (
            f"{type(erro_ping).__name__}: {erro_ping}"
        )
'''

if alvo not in texto:
    raise SystemExit("ERRO: trecho alvo não encontrado. Nenhuma alteração feita.")

if '"teste_bgutil_ping"' in texto:
    raise SystemExit("O teste_bgutil_ping já existe. Nenhuma alteração feita.")

arquivo.write_text(texto.replace(alvo, novo, 1), encoding="utf-8")
print("OK: teste_bgutil_ping acrescentado.")
