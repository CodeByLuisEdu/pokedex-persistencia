"""
persistencia.py
================
Camada de persistência do projeto Pokédex.

Implementa a gravação e leitura do dataset de Pokémon em QUATRO formatos:

    TEXTO (legível / portável)        BINÁRIO (menor / mais rápido)
    -------------------------         ----------------------------
    JSON  -> json.dump / json.load    pickle -> pickle.dump / pickle.load
    CSV   -> csv.DictWriter/Reader    struct -> struct.pack / unpack (registro fixo)

Conceitos demonstrados (exigidos no enunciado):
  * with open(...) sempre (fecha o arquivo automaticamente)
  * encoding="utf-8" em TODOS os arquivos de texto
  * modo binário ("wb"/"rb") nos formatos binários
  * tratamento do caso "arquivo ainda não existe" (FileNotFoundError)
  * medição de tempo de salvar e carregar
  * hexdump para mostrar o conteúdo ilegível do arquivo binário
"""

import csv
import json
import os
import pickle
import struct
import time

# ----------------------------------------------------------------------------
# Onde os arquivos ficam salvos
# ----------------------------------------------------------------------------
PASTA_DADOS = os.path.join(os.path.dirname(__file__), "dados")
os.makedirs(PASTA_DADOS, exist_ok=True)

ARQUIVOS = {
    "json":   os.path.join(PASTA_DADOS, "pokemons.json"),
    "csv":    os.path.join(PASTA_DADOS, "pokemons.csv"),
    "pickle": os.path.join(PASTA_DADOS, "pokemons.pkl"),
    "struct": os.path.join(PASTA_DADOS, "pokemons.bin"),
}

# Campos que descrevem cada Pokémon no nosso dataset simplificado.
# Todos os valores numéricos são inteiros -> facilita o struct.
CAMPOS = [
    "id", "name", "height", "weight", "base_experience",
    "hp", "attack", "defense", "special_attack", "special_defense", "speed",
]

# ----------------------------------------------------------------------------
# Layout do registro de tamanho fixo para o struct
# ----------------------------------------------------------------------------
# < = little-endian, sem padding de alinhamento
# I  = id              (unsigned int, 4 bytes)
# 20s = name           (20 bytes; texto utf-8 truncado/preenchido com \x00)
# 9H = os 9 inteiros restantes (unsigned short, 2 bytes cada)
#      height, weight, base_experience, hp, attack, defense,
#      special_attack, special_defense, speed
FORMATO_STRUCT = "<I20s9H"
TAM_NOME = 20
TAM_REGISTRO = struct.calcsize(FORMATO_STRUCT)  # = 42 bytes


# ============================================================================
# Helper de medição de tempo
# ============================================================================
def cronometrar(funcao, *args, **kwargs):
    """Executa `funcao`, devolve (resultado, tempo_em_ms)."""
    inicio = time.perf_counter()
    resultado = funcao(*args, **kwargs)
    duracao_ms = (time.perf_counter() - inicio) * 1000
    return resultado, round(duracao_ms, 3)


# ============================================================================
# Normalização do dado bruto da PokéAPI -> nosso dicionário enxuto
# ============================================================================
def simplificar_pokemon(bruto):
    """
    Recebe a resposta crua de /pokemon/{id} da PokéAPI e devolve só o que
    interessa, num dicionário plano e com tipos inteiros.
    """
    stats = {s["stat"]["name"]: s["base_stat"] for s in bruto.get("stats", [])}
    return {
        "id": int(bruto["id"]),
        "name": str(bruto["name"]),
        "height": int(bruto.get("height", 0)),
        "weight": int(bruto.get("weight", 0)),
        "base_experience": int(bruto.get("base_experience") or 0),
        "hp": int(stats.get("hp", 0)),
        "attack": int(stats.get("attack", 0)),
        "defense": int(stats.get("defense", 0)),
        "special_attack": int(stats.get("special-attack", 0)),
        "special_defense": int(stats.get("special-defense", 0)),
        "speed": int(stats.get("speed", 0)),
    }


# ============================================================================
# JSON  (texto)
# ============================================================================
def salvar_json(dados, caminho=ARQUIVOS["json"]):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def carregar_json(caminho=ARQUIVOS["json"]):
    # Se o arquivo ainda não existe, FileNotFoundError sobe para quem chamou.
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# CSV  (texto)
# ============================================================================
def salvar_csv(dados, caminho=ARQUIVOS["csv"]):
    # newline="" é a recomendação oficial do módulo csv para não duplicar \r\n
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        for p in dados:
            escritor.writerow({k: p[k] for k in CAMPOS})


def carregar_csv(caminho=ARQUIVOS["csv"]):
    with open(caminho, "r", encoding="utf-8", newline="") as f:
        leitor = csv.DictReader(f)
        dados = []
        for linha in leitor:
            # No CSV tudo volta como string -> reconvertemos os números.
            registro = {"name": linha["name"]}
            for k in CAMPOS:
                if k != "name":
                    registro[k] = int(linha[k])
            dados.append(registro)
        return dados


# ============================================================================
# pickle  (binário)
# ============================================================================
def salvar_pickle(dados, caminho=ARQUIVOS["pickle"]):
    with open(caminho, "wb") as f:                 # modo BINÁRIO de escrita
        pickle.dump(dados, f, protocol=pickle.HIGHEST_PROTOCOL)


def carregar_pickle(caminho=ARQUIVOS["pickle"]):
    with open(caminho, "rb") as f:                 # modo BINÁRIO de leitura
        return pickle.load(f)


# ============================================================================
# struct  (binário, registro de tamanho fixo)
# ============================================================================
def salvar_struct(dados, caminho=ARQUIVOS["struct"]):
    with open(caminho, "wb") as f:
        for p in dados:
            nome_bytes = p["name"].encode("utf-8")[:TAM_NOME]
            nome_bytes = nome_bytes.ljust(TAM_NOME, b"\x00")  # preenche até 20
            registro = struct.pack(
                FORMATO_STRUCT,
                p["id"],
                nome_bytes,
                p["height"], p["weight"], p["base_experience"],
                p["hp"], p["attack"], p["defense"],
                p["special_attack"], p["special_defense"], p["speed"],
            )
            f.write(registro)


def carregar_struct(caminho=ARQUIVOS["struct"]):
    dados = []
    with open(caminho, "rb") as f:
        while True:
            bloco = f.read(TAM_REGISTRO)
            if not bloco:            # fim do arquivo
                break
            if len(bloco) < TAM_REGISTRO:
                # registro incompleto -> arquivo corrompido; ignoramos a sobra
                break
            campos = struct.unpack(FORMATO_STRUCT, bloco)
            nome = campos[1].rstrip(b"\x00").decode("utf-8", errors="replace")
            dados.append({
                "id": campos[0],
                "name": nome,
                "height": campos[2],
                "weight": campos[3],
                "base_experience": campos[4],
                "hp": campos[5],
                "attack": campos[6],
                "defense": campos[7],
                "special_attack": campos[8],
                "special_defense": campos[9],
                "speed": campos[10],
            })
    return dados


# ============================================================================
# Tabela única de despacho -> usada pelos endpoints do Flask
# ============================================================================
SALVADORES = {
    "json": salvar_json,
    "csv": salvar_csv,
    "pickle": salvar_pickle,
    "struct": salvar_struct,
}
CARREGADORES = {
    "json": carregar_json,
    "csv": carregar_csv,
    "pickle": carregar_pickle,
    "struct": carregar_struct,
}

ROTULOS = {
    "json": "JSON (texto)",
    "csv": "CSV (texto)",
    "pickle": "pickle (binário)",
    "struct": "struct (binário)",
}


def salvar_todos(dados):
    """
    Salva o dataset nos 4 formatos e devolve, para cada um:
        tamanho em KB, tempo de salvar (ms) e tempo de carregar (ms).
    """
    relatorio = {}
    for fmt, salvar in SALVADORES.items():
        _, t_salvar = cronometrar(salvar, dados)
        _, t_carregar = cronometrar(CARREGADORES[fmt])
        tamanho_bytes = os.path.getsize(ARQUIVOS[fmt])
        relatorio[fmt] = {
            "rotulo": ROTULOS[fmt],
            "arquivo": os.path.basename(ARQUIVOS[fmt]),
            "tamanho_kb": round(tamanho_bytes / 1024, 2),
            "tamanho_bytes": tamanho_bytes,
            "tempo_salvar_ms": t_salvar,
            "tempo_carregar_ms": t_carregar,
        }
    return relatorio


def comparar():
    """Igual ao salvar_todos, mas só lê os arquivos que já existem em disco."""
    relatorio = {}
    for fmt in SALVADORES:
        caminho = ARQUIVOS[fmt]
        if not os.path.exists(caminho):
            relatorio[fmt] = {"rotulo": ROTULOS[fmt], "existe": False}
            continue
        _, t_carregar = cronometrar(CARREGADORES[fmt])
        tamanho_bytes = os.path.getsize(caminho)
        relatorio[fmt] = {
            "rotulo": ROTULOS[fmt],
            "existe": True,
            "arquivo": os.path.basename(caminho),
            "tamanho_kb": round(tamanho_bytes / 1024, 2),
            "tamanho_bytes": tamanho_bytes,
            "tempo_carregar_ms": t_carregar,
        }
    return relatorio


# ============================================================================
# Inspeção: trecho legível (texto) vs hexdump (binário)
# ============================================================================
def hexdump(caminho, max_bytes=256):
    """
    Gera um hexdump no estilo `hexdump -C`:
        offset    bytes em hexadecimal           |representação ASCII|
    """
    with open(caminho, "rb") as f:
        dados = f.read(max_bytes)

    linhas = []
    for offset in range(0, len(dados), 16):
        pedaco = dados[offset:offset + 16]
        hexa = " ".join(f"{b:02x}" for b in pedaco)
        hexa = hexa.ljust(47)  # 16 bytes * 3 chars - 1 = 47
        ascii_repr = "".join(chr(b) if 32 <= b < 127 else "." for b in pedaco)
        linhas.append(f"{offset:08x}  {hexa}  |{ascii_repr}|")
    return "\n".join(linhas)


def inspecionar(formato, max_chars=600):
    """
    Devolve um trecho do arquivo para exibir na tela.
      - texto (json/csv): retorna os primeiros caracteres legíveis.
      - binário (pickle/struct): retorna um hexdump (ilegível de propósito).
    """
    caminho = ARQUIVOS[formato]
    if not os.path.exists(caminho):
        return {"existe": False, "formato": formato}

    eh_texto = formato in ("json", "csv")
    if eh_texto:
        with open(caminho, "r", encoding="utf-8") as f:
            conteudo = f.read(max_chars)
        return {
            "existe": True, "formato": formato, "tipo": "texto",
            "rotulo": ROTULOS[formato], "conteudo": conteudo,
        }
    else:
        return {
            "existe": True, "formato": formato, "tipo": "binario",
            "rotulo": ROTULOS[formato], "conteudo": hexdump(caminho),
            "tam_registro": TAM_REGISTRO if formato == "struct" else None,
            "layout": FORMATO_STRUCT if formato == "struct" else None,
        }
