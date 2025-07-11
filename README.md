# LUMM-server

## Requisitos

- Python 3.9
- PostgreSQL rodando localmente ou via Docker

## Setup do Projeto

### 1️⃣ Clonar o repositório

```bash
git@github.com:G2BC/LUMM-server.git
cd LUMM-server
```

### 2️⃣ Criar e ativar o ambiente virtual (Recomendado)

```bash
python -m venv venv
source venv/bin/activate       # Linux/macOS
venv\Scripts\activate          # Windows
```

### 3️⃣ Instalar dependências

```bash
pip install -r requirements.txt
```

### 4️⃣ Configurar variáveis de ambiente

Crie um arquivo .env baseado no .env.example

### 5️⃣ Execute as migrações

```bash
flask db upgrade
```

### 6️⃣ Rodar o servidor em desenvolvimento

```bash
python wsgi.py
```

## Comandos úteis

### Criar nova migration

```bash
flask db migrate -m "mensagem"
```

### Aplicar migrations

```bash
flask db upgrade
```

### Desativar o ambiente virtual

```bash
deactivate
```
