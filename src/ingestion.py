import os
import re
import glob
import time
from pathlib import Path
from pypdf import PdfReader
import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY não encontrada no arquivo .env!")

client = genai.Client(api_key=api_key)

# Modelo gratuito de embeddings do Google AI Studio
EMBEDDING_MODEL = "gemini-embedding-001"

# Free tier: 100 requisicoes/minuto para embed_content
SEGUNDOS_ENTRE_REQUESTS = 0.7

def _embed_com_retry(texto: str, max_tentativas: int = 5):
    """Chama embed_content com retry/backoff em caso de 429 (quota excedida)."""
    for tentativa in range(1, max_tentativas + 1):
        try:
            return client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texto
            )
        except ClientError as e:
            if e.code != 429 or tentativa == max_tentativas:
                raise
            espera = 30
            try:
                violacoes = e.details["error"]["details"]
                for v in violacoes:
                    if v.get("@type", "").endswith("RetryInfo"):
                        espera = float(v["retryDelay"].rstrip("s")) + 2
            except Exception:
                pass
            print(f"  Quota excedida, aguardando {espera:.0f}s antes de tentar novamente (tentativa {tentativa}/{max_tentativas})...")
            time.sleep(espera)

def extrair_texto_pdf(caminho_pdf: str) -> list[dict]:
    """Le um arquivo PDF e extrai o texto pagina a pagina com metadados."""
    reader = PdfReader(caminho_pdf)
    paginas = []
    nome_arquivo = Path(caminho_pdf).name
    
    for idx, pagina in enumerate(reader.pages):
        texto = pagina.extract_text() or ""
        if texto.strip():
            paginas.append({
                "texto": texto.strip(),
                "arquivo": nome_arquivo,
                "pagina": idx + 1
            })
    return paginas

def extrair_texto_markdown(caminho_md: str) -> list[dict]:
    """Le um arquivo Markdown e extrai o texto com metadados."""
    nome_arquivo = Path(caminho_md).name
    with open(caminho_md, "r", encoding="utf-8") as f:
        texto = f.read().strip()
    
    if texto:
        return [{
            "texto": texto,
            "arquivo": nome_arquivo,
            "pagina": 1
        }]
    return []

_SENTENCA_RE = re.compile(r'(?<=[.!?])\s+')

def criar_chunks(documentos_paginas: list[dict], chunk_size: int = 700, chunk_overlap: int = 100) -> list[dict]:
    """Divide os textos em blocos respeitando fronteiras de frase, com sobreposicao
    (por frases) entre blocos consecutivos para manter contexto semantico."""
    chunks = []

    for item in documentos_paginas:
        texto = item["texto"]
        sentencas = [s.strip() for s in _SENTENCA_RE.split(texto) if s.strip()]

        blocos: list[list[str]] = []
        atual: list[str] = []
        atual_len = 0

        for sent in sentencas:
            # Sentenca maior que o proprio chunk: particiona por caracteres
            if len(sent) > chunk_size:
                if atual:
                    blocos.append(atual)
                    atual, atual_len = [], 0
                passo = chunk_size - chunk_overlap
                for i in range(0, len(sent), passo):
                    blocos.append([sent[i:i + chunk_size]])
                continue

            if atual and atual_len + len(sent) + 1 > chunk_size:
                blocos.append(atual)

                # Overlap: mantem as ultimas frases do bloco anterior que cabem no overlap
                overlap_sentencas: list[str] = []
                overlap_len = 0
                for s in reversed(atual):
                    if overlap_len + len(s) + 1 > chunk_overlap:
                        break
                    overlap_sentencas.insert(0, s)
                    overlap_len += len(s) + 1
                atual, atual_len = overlap_sentencas, overlap_len

            atual.append(sent)
            atual_len += len(sent) + 1

        if atual:
            blocos.append(atual)

        for chunk_idx, bloco in enumerate(blocos, 1):
            trecho = " ".join(bloco).strip()
            if not trecho:
                continue
            chunk_id = f"{item['arquivo']}_p{item['pagina']}_c{chunk_idx}"
            chunks.append({
                "id": chunk_id,
                "texto": trecho,
                "arquivo": item["arquivo"],
                "pagina": item["pagina"],
                "chunk_idx": chunk_idx
            })

    return chunks

def indexar_no_chromadb(chunks: list[dict], path_db: str = None, collection_name: str = "askdata_knowledge"):
    """Gera embeddings e salva os chunks e metadados no ChromaDB local persistente."""
    if path_db is None:
        path_db = str(BASE_DIR / "chroma_db")
    chroma_client = chromadb.PersistentClient(path=path_db)
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    
    ja_indexados = set(collection.get(ids=[ch["id"] for ch in chunks])["ids"])
    pendentes = [ch for ch in chunks if ch["id"] not in ja_indexados]

    print(f"Total de chunks: {len(chunks)} | Ja indexados: {len(ja_indexados)} | Pendentes: {len(pendentes)}")

    for i, ch in enumerate(pendentes, 1):
        res = _embed_com_retry(ch["texto"])
        vetor = res.embeddings[0].values

        collection.upsert(
            ids=[ch["id"]],
            embeddings=[vetor],
            documents=[ch["texto"]],
            metadatas={
                "arquivo": ch["arquivo"],
                "pagina": ch["pagina"],
                "chunk_idx": ch["chunk_idx"]
            }
        )
        if i % 5 == 0 or i == len(pendentes):
            print(f"  -> Indexados {i}/{len(pendentes)} chunks pendentes...")
        time.sleep(SEGUNDOS_ENTRE_REQUESTS)
            
    print(f"Ingestao concluida com sucesso no ChromaDB ({path_db})! Total salvo: {collection.count()} chunks.")

if __name__ == "__main__":
    pasta_dados = str(BASE_DIR / "data")
    todos_documentos = []
    
    # 1. Carregar PDFs da pasta data
    for pdf_path in glob.glob(f"{pasta_dados}/*.pdf"):
        print(f"Processando PDF: {pdf_path}")
        todos_documentos.extend(extrair_texto_pdf(pdf_path))
        
    # 2. Carregar Markdowns da pasta data
    for md_path in glob.glob(f"{pasta_dados}/*.md"):
        print(f"Processando Markdown: {md_path}")
        todos_documentos.extend(extrair_texto_markdown(md_path))
        
    if not todos_documentos:
        print("Nenhum arquivo PDF ou Markdown encontrado em ./data! Adicione arquivos na pasta para testar.")
    else:
        # 3. Gerar Chunks
        lista_chunks = criar_chunks(todos_documentos, chunk_size=700, chunk_overlap=100)
        # 4. Indexar no ChromaDB
        indexar_no_chromadb(lista_chunks)