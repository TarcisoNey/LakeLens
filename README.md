# AskData - LakeLens
Projeto do grupo de estudos da IA Data Lakers + Navi.

**Integrantes:**
- Ana Cristina Schmidt
- Tarciso Ney

**Domínio temático:** Engenharia de Dados & DevOps

## Objetivo
Desenvolver um assistente baseado em RAG (Retrieval-Augmented Generation) para responder perguntas sobre engenharia de dados, arquiteturas centradas em dados, Lakehouse e Delta Lake.

As respostas serão geradas com base nos documentos selecionados, com indicação da fonte e da página utilizada.

## 📝 Documentos
1. PATRIKAR, Apoorva; GANTARAM, Santosh. **Best Practices for Designing and Implementing Modern Data-Centric Architecture Use Cases**. AWS Prescriptive Guidance, 2023.

2. ARMBRUST, Michael et al. **Lakehouse: A New Generation of Open Platforms that Unify Data Warehousing and Advanced Analytics**. CIDR, 2021.

3. ARMBRUST, Michael et al. **Delta Lake: High-Performance ACID Table Storage over Cloud Object Stores**. PVLDB, 2020.

## Inicialização do projeto

**Pré-requisitos:** Python 3 e uma chave da API do Gemini (Google AI Studio).

1. Clone o repositório e entre na pasta:
```bash
   git clone <url-do-repositorio>
   cd <nome-da-pasta>
```

2. Crie o ambiente virtual (só na primeira vez):

   macOS / Linux:
```bash
   python3 -m venv .venv
```
   Windows:
```bash
   python -m venv .venv
```

3. Ative o ambiente virtual (a cada novo terminal):

   macOS / Linux:
```bash
   source .venv/bin/activate
```
   Windows:
```bash
   .venv\Scripts\activate
```

4. Instale as dependências:

   macOS / Linux:
```bash
   python3 -m pip install -r requirements.txt
```
   Windows:
```bash
   python -m pip install -r requirements.txt
```

5. Configure a chave da API. Copie o modelo e edite o `.env` com a sua chave (o `.env` não vai para o Git):

   macOS / Linux / PowerShell:
```bash
   cp .env.example .env
```
   Prompt de Comando (Windows):
```bash
   copy .env.example .env
```

6. Valide o ambiente com o smoke test:

   macOS / Linux:
```bash
   python3 check_setup.py
```
   Windows:
```bash
   python check_setup.py
```

7. Quando terminar, saia do ambiente virtual:
```bash
   deactivate
```
