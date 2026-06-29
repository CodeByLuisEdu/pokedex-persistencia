"""
app.py
======
Backend Flask do projeto Pokédex — Persistência de Dados.

Responsabilidades:
  * servir o frontend (static/index.html)
  * baixar o dataset da PokéAPI                  -> GET  /api/carregar
  * gravar o dataset em disco nos 4 formatos     -> POST /api/salvar
  * ler o dataset do disco (modo OFFLINE)        -> GET  /api/offline
  * comparar tamanho/tempo de cada formato       -> GET  /api/comparar
  * inspecionar arquivo (texto vs hexdump)       -> GET  /api/inspecionar

Rode com:  python app.py    (abre em http://localhost:5000)
"""

import os
from concurrent.futures import ThreadPoolExecutor

import requests
from flask import Flask, jsonify, request, send_from_directory

import persistencia as pers

# Pasta onde este arquivo (app.py) está. O index.html fica aqui, ao lado dele.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

POKEAPI = "https://pokeapi.co/api/v2"


# ----------------------------------------------------------------------------
# Frontend
# ----------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/busca")
def busca():
    return send_from_directory(BASE_DIR, "busca.html")


# ----------------------------------------------------------------------------
# GET /api/carregar?limite=151
# Baixa da PokéAPI e devolve o dataset já simplificado (NÃO salva ainda).
# ----------------------------------------------------------------------------
def _buscar_um(session, url):
    bruto = session.get(url, timeout=15).json()
    return pers.simplificar_pokemon(bruto)


@app.route("/api/carregar")
def carregar_da_api():
    try:
        limite = int(request.args.get("limite", 151))
    except ValueError:
        limite = 151
    limite = max(1, min(limite, 1025))  # limites de segurança

    try:
        session = requests.Session()
        lista = session.get(
            f"{POKEAPI}/pokemon", params={"limit": limite}, timeout=15
        ).json()["results"]
        urls = [item["url"] for item in lista]

        # baixa os detalhes em paralelo para não demorar demais
        with ThreadPoolExecutor(max_workers=16) as pool:
            dados = list(pool.map(lambda u: _buscar_um(session, u), urls))

        dados.sort(key=lambda p: p["id"])
        return jsonify({"ok": True, "total": len(dados), "dados": dados})
    except requests.RequestException as e:
        return jsonify({"ok": False, "erro": f"Falha ao acessar a PokéAPI: {e}"}), 502


# ----------------------------------------------------------------------------
# POST /api/salvar   body: { "dados": [...] }
# Grava nos 4 formatos e devolve o relatório de tamanho + tempo.
# ----------------------------------------------------------------------------
@app.route("/api/salvar", methods=["POST"])
def salvar():
    corpo = request.get_json(silent=True) or {}
    dados = corpo.get("dados")
    if not isinstance(dados, list) or not dados:
        return jsonify({"ok": False, "erro": "Envie 'dados' como uma lista não vazia."}), 400
    try:
        relatorio = pers.salvar_todos(dados)
        return jsonify({"ok": True, "total": len(dados), "formatos": relatorio})
    except (OSError, KeyError, TypeError) as e:
        return jsonify({"ok": False, "erro": f"Erro ao salvar: {e}"}), 500


# ----------------------------------------------------------------------------
# GET /api/offline?formato=json   (json | csv | pickle | struct)
# Lê do disco SEM tocar na internet. É o coração do "modo offline".
# ----------------------------------------------------------------------------
@app.route("/api/offline")
def offline():
    formato = request.args.get("formato", "json")
    if formato not in pers.CARREGADORES:
        return jsonify({"ok": False, "erro": f"Formato inválido: {formato}"}), 400
    try:
        dados = pers.CARREGADORES[formato]()
        return jsonify({"ok": True, "formato": formato, "total": len(dados), "dados": dados})
    except FileNotFoundError:
        # Caso obrigatório do enunciado: "arquivo ainda não existe".
        return jsonify({
            "ok": False,
            "erro": f"O arquivo '{pers.ARQUIVOS[formato]}' ainda não existe. "
                    f"Carregue da API e salve primeiro.",
        }), 404
    except (OSError, ValueError) as e:
        return jsonify({"ok": False, "erro": f"Erro ao ler o arquivo: {e}"}), 500


# ----------------------------------------------------------------------------
# GET /api/comparar   -> tamanho (KB) + tempo de carregar de cada formato
# ----------------------------------------------------------------------------
@app.route("/api/comparar")
def comparar():
    return jsonify({"ok": True, "formatos": pers.comparar()})


# ----------------------------------------------------------------------------
# GET /api/inspecionar?formato=json  -> trecho de texto OU hexdump
# ----------------------------------------------------------------------------
@app.route("/api/inspecionar")
def inspecionar():
    formato = request.args.get("formato", "json")
    if formato not in pers.ARQUIVOS:
        return jsonify({"ok": False, "erro": f"Formato inválido: {formato}"}), 400
    resultado = pers.inspecionar(formato)
    if not resultado.get("existe"):
        return jsonify({"ok": False, "erro": "Arquivo ainda não existe."}), 404
    return jsonify({"ok": True, **resultado})


if __name__ == "__main__":
    # host=0.0.0.0 facilita testar de outro dispositivo na mesma rede / deploy
    app.run(host="0.0.0.0", port=5000, debug=True)
