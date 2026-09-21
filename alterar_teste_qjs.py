from pathlib import Path

arquivo = Path("usuarios/views.py")
texto = arquivo.read_text(encoding="utf-8")

marcador = '        resultado["etapa"] = "criando_youtube_dl"\n'

bloco = '''        # Teste real de execução do QuickJS
        resultado["teste_qjs_execucao"] = {
            "tentado": False,
            "ok": False,
            "saida": "",
            "erro": "",
        }

        if os.path.isfile(qjs_path) and os.access(qjs_path, os.X_OK):
            resultado["teste_qjs_execucao"]["tentado"] = True

            try:
                teste_qjs = subprocess.run(
                    [qjs_path, "-e", "print(1 + 2)"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                resultado["teste_qjs_execucao"]["ok"] = (
                    teste_qjs.returncode == 0
                    and teste_qjs.stdout.strip() == "3"
                )
                resultado["teste_qjs_execucao"]["saida"] = (
                    teste_qjs.stdout.strip()
                )
                resultado["teste_qjs_execucao"]["erro"] = (
                    teste_qjs.stderr.strip()
                )

            except Exception as erro_qjs:
                resultado["teste_qjs_execucao"]["erro"] = (
                    f"{type(erro_qjs).__name__}: {erro_qjs}"
                )

        resultado["etapa"] = "criando_youtube_dl"
'''

if marcador not in texto:
    raise SystemExit("ERRO: marcador não encontrado.")

if '"teste_qjs_execucao"' in texto:
    raise SystemExit("ERRO: teste QJS já existe no arquivo.")

texto = texto.replace(marcador, bloco, 1)

arquivo.write_text(texto, encoding="utf-8")

print("OK - teste real do QuickJS inserido.")
