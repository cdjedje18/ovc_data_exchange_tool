# Ukwaba

Platataforma de interoperabilidade

### 1. Criação ambiente virtual
```sh
python -m venv .venv
```

### 2. Activação do ambiente virtual
O comando de activação para o sistema operativo Windows
```sh
. .venv/Scripts/activate
```

### 3. Instalação dependências
```sh
pip install -r requirements.txt
```

### 4. Actualização das variáveis de ambiente
Crie o ficheiro .env no root da pasta do projecto e preencha as seguintes variáveis:

```sh
DB_NAME=""
DB_USER=""
DB_PASSWORD=""
DB_HOST=""
DB_PORT=""

EMAIL_HOST = ""
EMAIL_PORT = ""
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = ""
EMAIL_USE_SSL = ""
```

### 5. Executar migração da base de dados

#### 5.1. Criação das migrations
```sh
python manage.py makemigrations user core data_exchange data_exchange_routes big_data_export orgunit_sync notification ws_messaging
```

#### 5.2. Criação das migrations para as views da base de dados
```sh
python manage.py makeviewmigrations core data_exchange notification orgunit_sync
```

#### 5.3. Execução das migrations da base de dados
```sh
python manage.py migrate
```

### 6. Inicialização do servidor
```sh
# python manage.py runserver

daphne core.asgi:application

```
### 7. Instalação do Redis e celery
 Instalação do Redis no sistema operativo
Linux: https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/ ou no windows através do link
https://github.com/tporadowski/redis/releases .
```sh
Actualizar as bibliotecas do redis no requirments
```

### 8. Instalação do Redis globalmente no sistema operativo
```sh
pip install Redis
```
### 9. Acompanhar requests do Redis na console
```
celery -A core.celery worker --loglevel=info --pool=solo -l INFO
```
