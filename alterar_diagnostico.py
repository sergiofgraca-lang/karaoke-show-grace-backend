from pathlib import Path

p = Path(r".\usuarios\views.py")
s = p.read_text(encoding="utf-8")

old = """        resultado["node_candidatos"] = {
            caminho: {
                "existe": os.path.exists(caminho),
                "executavel": os.path.isfile(caminho) and os.access(caminho, os.X_OK),
            }
            for caminho in [
                "/usr/bin/node",
                "/usr/local/bin/node",
                "/opt/bin/node",
                "/var/task/node",
                "/var/task/nodejs/node",
            ]
        }"""

new = """        resultado["runtime_candidatos"] = {
            caminho: {
                "existe": os.path.exists(caminho),
                "executavel": os.path.isfile(caminho) and os.access(caminho, os.X_OK),
            }
            for caminho in [
                "/usr/bin/node",
                "/usr/local/bin/node",
                "/opt/bin/node",
                "/var/task/node",
                "/var/task/nodejs/node",
                "/usr/bin/deno",
                "/usr/local/bin/deno",
                "/opt/bin/deno",
                "/var/task/deno",
                "/usr/bin/bun",
                "/usr/local/bin/bun",
                "/opt/bin/bun",
                "/var/task/bun",
                "/usr/bin/qjs",
                "/usr/local/bin/qjs",
                "/opt/bin/qjs",
            ]
        }"""

if old not in s:
    raise SystemExit("BLOCO node_candidatos NAO ENCONTRADO")

p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("OK - diagnostico ampliado")
