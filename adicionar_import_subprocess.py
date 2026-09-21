from pathlib import Path

arquivo = Path("usuarios/views.py")
texto = arquivo.read_text(encoding="utf-8")

alvo = "import shutil\n"

if "import subprocess\n" in texto:
    print("OK - subprocess já está importado.")
elif alvo not in texto:
    raise SystemExit("ERRO - import shutil não encontrado.")
else:
    texto = texto.replace(
        alvo,
        alvo + "import subprocess\n",
        1
    )
    arquivo.write_text(texto, encoding="utf-8")
    print("OK - import subprocess adicionado.")
