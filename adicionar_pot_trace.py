from pathlib import Path

arquivo = Path(r".\usuarios\views.py")
texto = arquivo.read_text(encoding="utf-8")

alvo = '''    ydl_opts = {
        "quiet": False,
        "no_warnings": False,
        "nocheckcertificate": True,
        "fetch_pot": "always",
'''

novo = '''    ydl_opts = {
        "quiet": False,
        "no_warnings": False,
        "nocheckcertificate": True,
        "fetch_pot": "always",
        "extractor_args": {
            "youtube": {
                "pot_trace": ["true"],
            },
        },
'''

if alvo not in texto:
    raise SystemExit("ERRO: trecho alvo não encontrado. Nenhuma alteração feita.")

if '"pot_trace"' in texto:
    raise SystemExit("pot_trace já existe. Nenhuma alteração feita.")

arquivo.write_text(texto.replace(alvo, novo, 1), encoding="utf-8")
print("OK: pot_trace acrescentado somente ao diagnóstico.")
