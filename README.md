# LUMM-server

## Requisitos

- Python 3.12
- uv (https://docs.astral.sh/uv/getting-started/installation/)
- PostgreSQL rodando localmente ou via Docker

## Setup do Projeto

### 1️⃣ Clonar o repositório

```bash
git clone git@github.com:G2BC/LUMM.git
cd backend
```

### 2️⃣ Sincronizar dependências com uv

```bash
uv sync --dev
```

### 3️⃣ Ativar o ambiente virtual (Opcional)

```bash
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate          # Windows
```

### 4️⃣ Configurar variáveis de ambiente

Crie um arquivo .env baseado no .env.example

### 5️⃣ Execute as migrações

```bash
uv run flask db upgrade
```

### 6️⃣ Rodar o servidor em desenvolvimento

```bash
uv run python wsgi.py
```

## Comandos úteis

### Criar nova migration

```bash
uv run flask db migrate -m "mensagem"
```

### Aplicar migrations

```bash
uv run flask db upgrade
```

### Desativar o ambiente virtual

```bash
deactivate
```

### ⚠️ Mantenha as regras de Lint e Formatação

Para garantir a consistência e a qualidade do código neste projeto, **antes de mesclar uma PR**, certifique-se de que seu código passou na ferramenta de lint e formatação (`ruff`) durante a execução da action de CI.

### 🛠️ Dicas

Rode `uv run ruff check .` e `uv run ruff format .` antes de commitar.

## 📄 Licença

Distribuído sob a Licença MIT. Veja `LICENSE` para mais informações.
