# Pokédex · Persistência de Dados (Texto vs Binário)

Trabalho Final da disciplina — camada de persistência para um app de
**ordenação e busca** de Pokémon. Antes, o app baixava tudo da API a cada
abertura; agora um **backend Python (Flask)** grava o dataset em disco em
**quatro formatos** (texto e binário) e o sistema passa a funcionar **offline**.

> **API usada:** [PokéAPI](https://pokeapi.co/) — endpoints `/pokemon?limit=151`
> (Geração 1) e `/pokemon/{id}` para os detalhes (altura, peso, experiência base e
> os 6 atributos de status).

---

## 🎯 O que o projeto faz

- Baixa os 151 Pokémon da PokéAPI e os mostra em cards.
- **Ordena** por número, nome, peso, altura, experiência base ou total de
  atributos; e **busca** por nome ou número.
- **Salva o dataset em disco** nos 4 formatos com um clique.
- **Modo offline:** reconstrói a tela lendo do arquivo, **sem tocar na internet**.
- **Painel comparativo:** tamanho (KB) + tempo de salvar e de carregar por formato.
- **Inspeção:** trecho legível do arquivo de texto **ao lado** do *hexdump*
  (ilegível) do arquivo binário.

A ordenação e a busca operam sobre o dataset **em memória**, venha ele da API
**ou** do arquivo — então tudo continua funcionando offline.

---

## 🧩 Formatos implementados (os 4 — pontos extras)

| Coluna | Formato | Como é gravado | Arquivo |
|---|---|---|---|
| **Texto** | **JSON** | `json.dump` / `json.load` | `dados/pokemons.json` |
| **Texto** | **CSV** | `csv.DictWriter` / `DictReader` | `dados/pokemons.csv` |
| **Binário** | **pickle** | `pickle.dump` / `pickle.load` | `dados/pokemons.pkl` |
| **Binário** | **struct** | `struct.pack` / `unpack` (registro fixo) | `dados/pokemons.bin` |

### Registro de tamanho fixo do `struct`

Cada Pokémon vira um bloco de **42 bytes** com o layout `"<I20s9H"`:

```
< little-endian, sem padding
I    id                 -> unsigned int   (4 bytes)
20s  name               -> 20 bytes utf-8 (truncado/preenchido com \x00)
9H   height, weight, base_experience,
     hp, attack, defense,
     special_attack, special_defense, speed
                        -> 9 × unsigned short (2 bytes cada = 18 bytes)
                                                         total = 42 bytes
```

Como todo registro tem o mesmo tamanho, a leitura é um laço simples de
`f.read(42)` + `struct.unpack`.

---

## 📊 Resultados da comparação (151 Pokémon)

Medição real do dataset da Geração 1 (os tempos variam por execução/máquina):

| Formato | Tamanho | Salvar | Carregar |
|---|---:|---:|---:|
| JSON (texto) | 35,2 KB | ~2,6 ms | ~3,0 ms |
| CSV (texto) | 7,3 KB | ~0,7 ms | ~0,6 ms |
| pickle (binário) | 9,0 KB | ~0,2 ms | ~0,2 ms |
| **struct (binário)** | **6,2 KB** ★ | **~0,2 ms** | **~0,1 ms** |

### Qual ganhou em tamanho/tempo — e por quê

- **`struct` venceu em tamanho e tempo.** Ele guarda só os bytes crus dos
  números (2–4 bytes por campo) sem nenhum texto de marcação. Não há nomes de
  campo, vírgulas, aspas nem chaves — daí o menor arquivo e a leitura mais rápida.
- **JSON foi o maior.** É o mais legível e portável, mas **repete o nome de cada
  campo em todos os 151 registros** (`"special_defense": ...` 151 vezes) e ainda
  leva indentação. Essa repetição é o preço da legibilidade.
- **CSV ficou surpreendentemente compacto** para um formato de texto, porque
  escreve os nomes das colunas **uma única vez** (no cabeçalho) e só os valores
  depois. Em troca, perde os tipos: tudo volta como `string` e precisa ser
  reconvertido para `int` na leitura.
- **pickle** é binário e rápido, mas carrega metadados do próprio protocolo
  Python, ficando um pouco maior que o `struct`. Vantagem: serializa qualquer
  objeto Python sem você definir um layout. **Cuidado:** `pickle` só deve ser
  lido de fontes confiáveis (pode executar código ao desserializar).

**Resumo:** binário (struct) ganha em eficiência; texto (JSON) ganha em
legibilidade e interoperabilidade. CSV é um bom meio-termo para dados tabulares.

---

## 🏗️ Arquitetura

```
[ Frontend JS (static/index.html) ]
        |  fetch (mesma origem)
        v
[ Backend Flask (app.py) ]
  GET  /                      -> serve o frontend
  GET  /api/carregar?limite=  -> baixa da PokéAPI e devolve os dados
  POST /api/salvar            -> grava em disco nos 4 formatos (+ tamanho/tempo)
  GET  /api/offline?formato=  -> lê do arquivo salvo (SEM internet)
  GET  /api/comparar          -> tamanho (KB) + tempo de cada formato
  GET  /api/inspecionar?formato= -> trecho de texto OU hexdump
        |
        v
[ persistencia.py ]  -> toda a lógica de leitura/escrita dos 4 formatos
```

```
pokedex-persistencia/
├── app.py             # backend Flask (rotas/API + serve o index.html)
├── persistencia.py    # núcleo: salvar/carregar nos 4 formatos + hexdump
├── index.html         # frontend (ordenação, busca, offline, comparação, inspeção)
├── dados/             # cache em disco (gerado em runtime; ignorado no git)
├── requirements.txt
└── README.md
```

---

## ▶️ Como rodar

```bash
# 1. criar ambiente e instalar dependências
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. subir o servidor
python app.py

# 3. abrir no navegador
#    http://localhost:5000
```

### Roteiro de teste (e como provar que funciona offline)

1. Clique em **⬇️ Carregar da API** (precisa de internet).
2. Clique em **💾 Salvar em disco** → veja o painel de comparação se preencher.
3. Olhe a **Inspeção**: alterne entre JSON/CSV (texto legível) e pickle/struct
   (hexdump ilegível).
4. **Desligue o Wi-Fi / desconecte a internet.**
5. Escolha um formato em **Offline** e clique em **📂 Carregar do arquivo** —
   a tela é remontada a partir do disco.
6. Use a **busca** e a **ordenação**: continuam funcionando com os dados do arquivo.

---

## ✅ Robustez (requisitos do enunciado)

- **`with open(...)`** em todas as operações de arquivo (fecha sozinho).
- **`encoding="utf-8"`** em todos os arquivos de texto (nomes com acento ok).
- Modo **binário** (`"wb"`/`"rb"`) em pickle e struct.
- Caso **"arquivo ainda não existe"** tratado: `/api/offline` captura
  `FileNotFoundError` e responde **404** com uma mensagem clara em vez de quebrar.
- Validações: formato inválido → **400**; lista vazia no `salvar` → **400**;
  falha de rede na PokéAPI → **502**.

---

## 🤖 Uso de IA

Apoio de IA (Claude, Anthropic) na estruturação do backend, no layout do
registro `struct` e na redação deste README. A lógica foi revisada e testada
(round-trip dos 4 formatos confere com os dados originais, incluindo nomes
acentuados).

## 📝 Observação sobre os sprites

Os cards tentam mostrar a imagem oficial do Pokémon (servida pelo repositório de
sprites da PokéAPI, derivada do `id`). **Offline**, sem acesso à internet, a
imagem não carrega e o card mostra automaticamente o número (`#25`) no lugar — os
**dados** (nome, atributos, peso, altura) vêm 100% do arquivo local.
