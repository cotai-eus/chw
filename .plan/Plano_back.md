Okay, Engenheiro. Analisando os documentos `Plano.md` e `Plano_db.md`, podemos elaborar um plano técnico detalhado para o backend do Sistema de Automação de Licitações.

## Plano Técnico Detalhado do Backend

### 1. Arquitetura Geral

A arquitetura será um **Monólito Modularizado**, construído com FastAPI. Embora `Plano.md` mencione "Microsserviços", para a fase inicial e com foco em aprendizado, um monólito bem estruturado é mais gerenciável. Os módulos podem ser projetados de forma a facilitar uma futura extração para microsserviços, se necessário.

**Fluxo de Requisição Típico:**
`Cliente (React) -> Load Balancer/Reverse Proxy (Nginx em Docker) -> Uvicorn/Gunicorn -> FastAPI App -> Serviços -> CRUD/DB -> Resposta`

**Componentes Principais:**
1.  **API Gateway (FastAPI):** Ponto de entrada para todas as requisições HTTP.
2.  **Serviços de Negócio:** Lógica de aplicação para cada funcionalidade (Auth, Empresas, Editais, Cotações, IA, etc.).
3.  **Camada de Acesso a Dados (CRUD):** Abstrações para interagir com PostgreSQL e MongoDB.
4.  **Módulos de Integração:** Para Ollama, OpenAI, Google Calendar, Email.
5.  **Tarefas em Background (Celery):** Para processamento assíncrono (IA, relatórios, emails, sync).
6.  **Comunicação Real-time (WebSockets):** Para notificações e colaboração.
7.  **Bancos de Dados:** PostgreSQL (relacional), MongoDB (documentos), Redis (cache/filas/sessões).

### 2. Tecnologias e Versões Recomendadas (Estáveis para Docker)

*   **Linguagem:** Python 3.11.x
*   **Framework API:** FastAPI ~0.110.0 (ou mais recente estável)
*   **Servidor ASGI:** Uvicorn ~0.27.0 (com Gunicorn ~21.2.0 para workers em produção)
*   **ORM (PostgreSQL):** SQLAlchemy ~2.0.x (com asyncpg ~0.29.0 como driver)
*   **ODM (MongoDB):** Motor ~3.3.x
*   **Cliente Redis:** aioredis ~2.0.x
*   **Validação de Dados:** Pydantic (integrado ao FastAPI)
*   **Tarefas em Background:** Celery ~5.3.x (com Redis ou RabbitMQ como broker/backend)
*   **Autenticação:** python-jose[cryptography] ~3.3.0, passlib[bcrypt] ~1.7.4
*   **Migrações DB (PostgreSQL):** Alembic ~1.13.x
*   **Cliente HTTP (para IA/APIs externas):** httpx ~0.26.0
*   **Containerização:** Docker, Docker Compose
*   **IA Local:** Ollama (executando como um serviço separado, acessível via HTTP)
*   **Testes:** Pytest ~7.4.x, pytest-asyncio

### 2.1. Configuração Aprimorada com Pydantic Settings

Uma configuração robusta é fundamental para o projeto. Usaremos `pydantic-settings` para validação e tipagem das configurações:

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional, List
import secrets

class Settings(BaseSettings):
    # API
    PROJECT_NAME: str = "Sistema de Automação de Licitações"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Database PostgreSQL
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # MongoDB
    MONGO_SERVER: str
    MONGO_USER: str
    MONGO_PASSWORD: str
    MONGO_DB: str
    MONGO_PORT: int = 27017
    
    @property
    def MONGO_DATABASE_URI(self) -> str:
        return f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}@{self.MONGO_SERVER}:{self.MONGO_PORT}/{self.MONGO_DB}"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    
    # IA Services
    OLLAMA_API_URL: str = "http://ollama:11434"
    OPENAI_API_KEY: Optional[str] = None
    AI_PROVIDER: str = "ollama"  # "ollama" ou "openai"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # File Upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".doc", ".docx"]
    UPLOAD_FOLDER: str = "/app/uploads"
    
    # Session Control (API Temporal)
    MAX_CONCURRENT_SESSIONS: int = 5
    SESSION_TIMEOUT_MINUTES: int = 30
    AUTO_RENEW_SESSION: bool = True
    
    # Email (SMTP)
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # Environment
    ENVIRONMENT: str = "development"  # "development", "staging", "production"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 3. Estrutura de Diretórios do Backend

Baseado no `Plano.md` e expandindo para boas práticas com FastAPI e Celery:

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py             # Dependências da API (ex: get_current_user)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py          # Agregador de todos os routers
│   │       └── endpoints/      # Routers por módulo (ex: auth.py, users.py, tenders.py)
│   │           ├── __init__.py
│   │           ├── auth.py
│   │           ├── companies.py
│   │           ├── users.py
│   │           ├── suppliers.py
│   │           ├── tenders.py
│   │           ├── quotes.py
│   │           ├── forms.py        # Baseado no Plano_db.md
│   │           ├── kanban.py       # Baseado no Plano_db.md
│   │           ├── calendar_integration.py
│   │           ├── reports.py
│   │           ├── admin.py        # Endpoints Master Admin
│   │           └── websockets.py   # Endpoints WebSocket centralizados
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Configurações (variáveis de ambiente)
│   │   ├── security.py         # Funções de hash de senha, criação/validação de JWT
│   │   └── logging.py          # Configuração de logging estruturado
│   ├── middleware/             # Middlewares customizados
│   │   ├── __init__.py
│   │   ├── session_middleware.py   # Para API Temporal
│   │   └── rate_limit_middleware.py
│   ├── exceptions/             # Exceções customizadas
│   │   ├── __init__.py
│   │   └── custom_exceptions.py
│   ├── crud/                   # Operações CRUD para cada modelo do banco
│   │   ├── __init__.py
│   │   ├── base.py             # CRUD base genérico
│   │   ├── crud_models.py      # Agregar todos os CRUDs
│   │   ├── crud_user.py
│   │   ├── crud_company.py
│   │   ├── crud_tender.py
│   │   ├── crud_user_session.py # Para API Temporal
│   │   └── ...                 # Outros CRUDS (supplier, product, quote, etc.)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base_class.py       # Base declarativa do SQLAlchemy
│   │   ├── session.py          # Configuração da sessão do banco (PostgreSQL, MongoDB)
│   │   ├── mongo_session.py    # Configuração específica MongoDB
│   │   └── models/             # Modelos SQLAlchemy (ex: user.py, company.py)
│   │       ├── __init__.py
│   │       ├── company.py
│   │       ├── user.py
│   │       ├── user_profile.py
│   │       ├── user_session.py
│   │       ├── form_template.py
│   │       ├── form_submission.py
│   │       ├── kanban.py # board, list, card, comment, member
│   │       ├── supplier.py
│   │       ├── product.py
│   │       ├── tender.py # tender, tender_item
│   │       ├── quote.py  # quote, quote_item
│   │       ├── calendar.py # calendar, event, attendee
│   │       ├── conversation.py # conversation, participant, message (metadata)
│   │       └── audit_log.py
│   ├── schemas/                # Modelos Pydantic para validação e serialização
│   │   ├── __init__.py
│   │   ├── token.py
│   │   ├── user.py
│   │   ├── company.py
│   │   ├── tender.py
│   │   ├── access_request.py
│   │   └── ...                 # Outros schemas
│   ├── services/               # Lógica de negócio, integrações com IA, etc.
│   │   ├── __init__.py
│   │   ├── email_service.py
│   │   ├── ia_processing_service.py # Ollama/OpenAI
│   │   ├── calendar_service.py    # Google Calendar
│   │   └── tender_analysis_service.py
│   ├── tasks/                  # Tarefas Celery
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Configuração da instância Celery
│   │   ├── email_tasks.py
│   │   ├── report_tasks.py
│   │   └── ia_tasks.py
│   ├── websockets/             # Lógica para WebSockets (chat, notificações real-time)
│   │   ├── __init__.py
│   │   ├── connection_manager.py
│   │   └── chat_handlers.py
│   ├── utils/                  # Utilitários gerais
│   │   └── __init__.py
│   ├── main.py                 # Ponto de entrada da aplicação FastAPI
│   └── __init__.py
├── alembic/                    # Configurações e migrações Alembic
│   ├── versions/
│   └── env.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── api/
│       └── v1/
│           └── test_users.py
├── .env.example
├── Dockerfile
├── docker-entrypoint.sh        # Script para rodar migrações antes de iniciar o app
├── pyproject.toml
└── README.md
```

### 4. Modelos de Dados (Pydantic e SQLAlchemy)

*   **SQLAlchemy Models (`app/db/models/`)**: Serão a representação das tabelas definidas em `Plano_db.md`. UUIDs como PKs são uma boa escolha. Exemplo: `user.py`:
    ```python
    # app/db/models/user.py
    import uuid
    from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, func, JSON, Enum as SAEnum
    from sqlalchemy.dialects.postgresql import UUID, INET
    from sqlalchemy.orm import relationship
    from app.db.base_class import Base
    from app.schemas.user import UserRole, UserStatus # Pydantic Enums

    class User(Base):
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
        email = Column(String(255), unique=True, index=True, nullable=False)
        password_hash = Column(String(255), nullable=False)
        first_name = Column(String(100), nullable=False)
        last_name = Column(String(100), nullable=False)
        avatar_url = Column(String(500), nullable=True)
        role = Column(SAEnum(UserRole, name="user_role_enum"), default=UserRole.USER, nullable=False)
        permissions = Column(JSON, default={})
        status = Column(SAEnum(UserStatus, name="user_status_enum"), default=UserStatus.PENDING, nullable=False)
        email_verified = Column(Boolean, default=False)
        must_change_password = Column(Boolean, default=False)
        last_login_at = Column(DateTime(timezone=True), nullable=True)
        password_changed_at = Column(DateTime(timezone=True), default=func.now())
        created_at = Column(DateTime(timezone=True), default=func.now())
        updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

        company = relationship("Company", back_populates="users")
        sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
        profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
        # ... outras relações (audit_logs, created_tenders, etc.)
    ```

*   **Pydantic Schemas (`app/schemas/`)**: Para validação de requests, formatação de responses e tipagem. Exemplo: `user.py`:
    ```python
    # app/schemas/user.py
    import uuid
    from enum import Enum
    from typing import Optional, Dict, List
    from pydantic import BaseModel, EmailStr, Field
    from datetime import datetime

    class UserRole(str, Enum):
        MASTER = "MASTER"
        ADMIN = "ADMIN_EMPRESA" # Renomeado para consistência
        MANAGER = "MANAGER"
        USER = "USER"
        VIEWER = "VIEWER"

    class UserStatus(str, Enum):
        ACTIVE = "ACTIVE"
        INACTIVE = "INACTIVE"
        PENDING = "PENDING"
        SUSPENDED = "SUSPENDED"

    class UserBase(BaseModel):
        email: EmailStr
        first_name: str = Field(..., min_length=1, max_length=100)
        last_name: str = Field(..., min_length=1, max_length=100)
        role: UserRole = UserRole.USER
        avatar_url: Optional[str] = None
        permissions: Optional[Dict[str, List[str]]] = {}

    class UserCreate(UserBase):
        password: str = Field(..., min_length=8)
        company_id: uuid.UUID # Adicionado para criação

    class UserUpdate(BaseModel):
        email: Optional[EmailStr] = None
        first_name: Optional[str] = Field(None, min_length=1, max_length=100)
        last_name: Optional[str] = Field(None, min_length=1, max_length=100)
        avatar_url: Optional[str] = None
        role: Optional[UserRole] = None
        permissions: Optional[Dict[str, List[str]]] = None
        status: Optional[UserStatus] = None
        must_change_password: Optional[bool] = None

    class UserInDBBase(UserBase):
        id: uuid.UUID
        company_id: uuid.UUID
        status: UserStatus
        email_verified: bool
        must_change_password: bool
        last_login_at: Optional[datetime] = None
        password_changed_at: Optional[datetime] = None
        created_at: datetime
        updated_at: datetime

        class Config:
            from_attributes = True # Anteriormente orm_mode

    class User(UserInDBBase): # Schema para responses
        pass

    class UserWithProfile(User): # Exemplo de schema com dados aninhados
        profile: Optional['UserProfile'] = None # Forward reference

    # ... UserProfile schemas ...
    # Definir 'UserProfile' aqui ou importar se estiver em outro arquivo
    # from app.schemas.user_profile import UserProfile # se em user_profile.py
    # UserWithProfile.model_rebuild() # para resolver forward references
    ```
    **Nota:** Todos os modelos do `Plano_db.md` (PostgreSQL e MongoDB) devem ter seus respectivos schemas Pydantic e, para PostgreSQL, modelos SQLAlchemy.

*   **MongoDB (Motor)**: Não há ORM/ODM estrito como SQLAlchemy. As interações serão feitas diretamente usando Motor, com validação nos schemas Pydantic antes da inserção/atualização. As coleções (`notifications`, `activity_history`, `dynamic_settings`, `dynamic_templates`, `ai_processing`) serão acessadas via `app.db.session.get_mongo_db()`.

### 5. Segurança e Autenticação

*   **Autenticação JWT:**
    *   Usar `python-jose` para criar e validar JWTs.
    *   Access tokens de curta duração (e.g., 15-60 minutos).
    *   Refresh tokens de longa duração (e.g., 7-30 dias), armazenados de forma segura (hashed) na tabela `user_sessions` do PostgreSQL.
    *   Endpoint `/auth/refresh` para obter novo access token usando um refresh token válido.
    *   Logout invalida o refresh token no banco.
*   **"API Temporal" (Controle de Sessões):**
    *   A tabela `user_sessions` é central.
    *   **Login:** Cria uma nova entrada em `user_sessions` com `token_hash` (do refresh token), `expires_at`, `last_activity`, `ip_address`, `user_agent`, etc.
    *   **Middleware de Autenticação/Sessão (`app/api/deps.py`):**
        1.  Valida o JWT (access token).
        2.  Obtém `session_id` do JWT (se incluído) ou busca a sessão ativa pelo `user_id` e `device_fingerprint` (se possível).
        3.  Verifica `user_sessions.is_active` e `user_sessions.expires_at`.
        4.  Atualiza `user_sessions.last_activity`.
        5.  **Renovação Inteligente:** Se `auto_renew` for `True` e a sessão estiver próxima de expirar (mas não expirada), e `last_activity` for recente, pode-se estender `expires_at` ou até mesmo emitir um novo access token silenciosamente.
        6.  **Controle de Concorrência:** Ao fazer login, verificar o número de sessões ativas para o `user_id` contra `companies.plan_type.max_concurrent_sessions` (a ser adicionado ao modelo Company) ou um limite global. Se excedido, invalidar a mais antiga ou negar login.
        7.  **Timeout por Inatividade:** Uma tarefa Celery periódica pode varrer `user_sessions` e desativar sessões onde `NOW() - last_activity > max_idle_minutes`.
    *   Endpoints:
        *   `GET /auth/sessions`: Lista sessões ativas do usuário (de `user_sessions`).
        *   `DELETE /auth/sessions/{session_id}`: Invalida uma sessão específica (marca `is_active=False`).
*   **Hashing de Senhas:** `passlib` com `bcrypt`.
*   **Autorização (RBAC):**
    *   FastAPI dependencies (`Depends`) para verificar roles e permissões.
    *   O campo `users.role` e `users.permissions` (JSONB) serão usados.
    *   Exemplo de dependência:
        ```python
        # app/api/deps.py
        from fastapi import Depends, HTTPException, status
        from fastapi.security import OAuth2PasswordBearer
        from app.core.security import decode_access_token
        from app.schemas.token import TokenPayload
        from app.schemas.user import UserRole
        from app.crud import crud_user
        from app.db.session import AsyncSessionLocal

        oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

        async def get_current_user(db: AsyncSessionLocal = Depends(get_db_session), token: str = Depends(oauth2_scheme)) -> models.User:
            credentials_exception = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            payload = decode_access_token(token) # Decodifica e valida expiração, etc.
            if payload is None or payload.username is None:
                raise credentials_exception
            token_data = TokenPayload(**payload)
            user = await crud_user.user.get_by_email(db, email=token_data.sub)
            if user is None or user.status != UserStatus.ACTIVE:
                raise credentials_exception
            return user

        def require_role(required_role: UserRole):
            async def role_checker(current_user: models.User = Depends(get_current_user)):
                if current_user.role != required_role and current_user.role != UserRole.MASTER: # Master tem acesso a tudo
                     # Ou verificar 'permissions' JSONB para granularidade
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
                return current_user
            return role_checker
        ```
*   **Validação de Input:** Pydantic em todos os endpoints.
*   **Isolamento de Dados por Empresa:** Quase todas as queries CRUD devem incluir um `company_id` no filtro `WHERE`. O `company_id` do usuário logado será usado.
*   **HTTPS:** Mandatório em produção (configurado no Nginx/Load Balancer).
*   **CORS:** Configurado no FastAPI para permitir requisições do frontend.

### 5.1. Middleware de Sessão Aprimorado

```python
# app/middleware/session_middleware.py
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import decode_access_token
from app.crud.crud_user_session import crud_user_session
from app.db.session import get_db
from datetime import datetime, timedelta

class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Aplicar apenas em rotas protegidas
        if self._should_check_session(request.url.path):
            await self._validate_session(request)
        
        response = await call_next(request)
        return response
    
    def _should_check_session(self, path: str) -> bool:
        excluded_paths = ["/auth/login", "/auth/register", "/docs", "/redoc"]
        return not any(path.startswith(exc) for exc in excluded_paths)
    
    async def _validate_session(self, request: Request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return
        
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        
        if payload and payload.get("session_id"):
            async with get_db() as db:
                session = await crud_user_session.get(db, id=payload["session_id"])
                if session and session.is_active:
                    # Atualizar last_activity
                    await crud_user_session.update(
                        db, db_obj=session, 
                        obj_in={"last_activity": datetime.utcnow()}
                    )
```

### 5.2. Sistema de Exceções Customizadas

```python
# app/exceptions/custom_exceptions.py
from fastapi import HTTPException, status

class BusinessLogicException(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class SessionExpiredException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"}
        )

class InsufficientPermissionsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )

class CompanyIsolationException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: resource belongs to different company"
        )

class TenderProcessingException(HTTPException):
    def __init__(self, detail: str = "Error processing tender document"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )
```

### 6. Integração com IA (Ollama e OpenAI API)

*   **Serviço de IA (`app/services/ia_processing_service.py`):**
    *   Abstrai a comunicação com Ollama (local) e OpenAI API (remota).
    *   Configuração via `app/core/config.py` para URLs, modelos, chaves API.
    ```python
    # app/services/ia_processing_service.py
    import httpx
    from app.core.config import settings

    class IAProcessingService:
        async def process_document_ollama(self, file_content: bytes, prompt: str, model_name: str = "llama3"):
            # Assumindo que Ollama está rodando e acessível via HTTP
            # Pode ser necessário converter file_content para texto antes ou enviar como base64
            # dependendo de como o modelo Ollama é exposto
            # Exemplo simplificado para extração de texto
            text_content = self._extract_text_from_file(file_content) # Implementar _extract_text_from_file
            
            async with httpx.AsyncClient(base_url=settings.OLLAMA_API_URL, timeout=120.0) as client:
                response = await client.post("/api/generate", json={
                    "model": model_name,
                    "prompt": f"{prompt}\n\nDocumento:\n{text_content}",
                    "stream": False
                })
                response.raise_for_status()
                return response.json().get("response") # ou a estrutura de dados relevante

        async def process_document_openai(self, file_content: bytes, prompt: str, model_name: str = "gpt-4-turbo-preview"):
            text_content = self._extract_text_from_file(file_content)
            # Similar, usando a biblioteca da OpenAI ou httpx
            # ...
            pass

        def _extract_text_from_file(self, file_content: bytes, file_type: str = "pdf") -> str:
            # Usar bibliotecas como PyPDF2, python-docx, etc.
            # Este é um passo CRÍTICO e pode ser complexo.
            if file_type == "pdf":
                # Exemplo com PyMuPDF (fitz)
                import fitz # PyMuPDF
                doc = fitz.open(stream=file_content, filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
                return text
            # ... outros formatos
            raise NotImplementedError(f"File type {file_type} not supported for text extraction.")

    ia_service = IAProcessingService()
    ```
*   **Upload de Editais:**
    *   Endpoint `POST /api/tenders/upload` recebe o arquivo.
    *   Salva o arquivo temporariamente ou em S3/MinIO.
    *   Cria uma entrada na tabela `tenders` com status `ANALYZING`.
    *   Dispara uma tarefa Celery (`app/tasks/ia_tasks.py`) para processamento.
*   **Tarefa Celery para IA:**
    1.  Recebe `tender_id` e `file_path`.
    2.  Lê o arquivo.
    3.  Chama `ia_service.process_document_ollama()` (ou OpenAI) com prompts otimizados.
        *   Prompts podem ser armazenados em config ou até em uma tabela `prompt_templates`.
    4.  Analisa a resposta da IA (JSON, texto estruturado).
    5.  Atualiza `tenders.processed_data` e `tenders.risk_score`.
    6.  Registra em `ai_processing` (MongoDB).
    7.  Atualiza `tenders.status` para `READY` ou `NEEDS_REVIEW`.
*   **Cache com Redis:**
    *   Resultados de processamento de IA para arquivos idênticos (hash do arquivo como chave) podem ser cacheados.
    *   `Plano.md` menciona "Cache inteligente com Redis" em "Semana 15: IA e Análise".

### 7. Comunicação com Frontend (React + TypeScript)

*   **REST API:** Endpoints definidos em `app/api/v1/endpoints/`.
*   **Documentação API:** FastAPI gera automaticamente documentação OpenAPI (`/docs`) e ReDoc (`/redoc`). Isso será crucial para o time de frontend.
*   **Schemas Pydantic:** Definem os contratos de dados entre backend e frontend.
*   **WebSockets (`app/websockets/`):**
    *   Para notificações em tempo real (novos editais, respostas de cotações, menções em chat).
    *   Para colaboração (edição de cotações, atualizações em Kanban).
    *   Usar um `ConnectionManager` para gerenciar conexões ativas.
    *   Exemplo básico:
        ```python
        # app/websockets/connection_manager.py
        from fastapi import WebSocket
        from typing import List, Dict
        import uuid

        class ConnectionManager:
            def __init__(self):
                self.active_connections: Dict[uuid.UUID, List[WebSocket]] = {} # user_id: [websockets]

            async def connect(self, websocket: WebSocket, user_id: uuid.UUID):
                await websocket.accept()
                if user_id not in self.active_connections:
                    self.active_connections[user_id] = []
                self.active_connections[user_id].append(websocket)

            def disconnect(self, websocket: WebSocket, user_id: uuid.UUID):
                if user_id in self.active_connections:
                    self.active_connections[user_id].remove(websocket)
                    if not self.active_connections[user_id]:
                        del self.active_connections[user_id]

            async def send_personal_message(self, message: str, user_id: uuid.UUID):
                if user_id in self.active_connections:
                    for connection in self.active_connections[user_id]:
                        await connection.send_text(message)
        
        manager = ConnectionManager()
        ```
        Endpoint WebSocket em `chat_handlers.py` ou similar.

### 8. Background Tasks, Cache, Filas (Celery + Redis)

*   **Celery (`app/tasks/`):**
    *   **Broker:** Redis (mais simples para começar) ou RabbitMQ (mais robusto).
    *   **Backend de Resultados:** Redis ou PostgreSQL.
    *   **Configuração Otimizada:**
        ```python
        # app/tasks/celery_app.py
        from celery import Celery
        from celery.schedules import crontab
        from app.core.config import settings

        celery_app = Celery(
            "worker",
            broker=settings.REDIS_URL,
            backend=settings.REDIS_URL,
            include=[
                "app.tasks.ia_tasks",
                "app.tasks.email_tasks", 
                "app.tasks.report_tasks",
                "app.tasks.session_tasks"
            ]
        )

        # Configurações otimizadas
        celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_time_limit=30 * 60,  # 30 minutos
            task_soft_time_limit=25 * 60,  # 25 minutos
            worker_prefetch_multiplier=1,
            worker_max_tasks_per_child=1000,
        )

        # Tarefas periódicas
        celery_app.conf.beat_schedule = {
            "cleanup-expired-sessions": {
                "task": "app.tasks.session_tasks.cleanup_expired_sessions",
                "schedule": crontab(minute=0),  # A cada hora
            },
            "process-pending-ia-tasks": {
                "task": "app.tasks.ia_tasks.process_pending_tasks",
                "schedule": crontab(minute="*/5"),  # A cada 5 minutos
            },
        }
        ```
    *   **Tarefas:**
        *   Processamento de editais com IA (`ia_tasks.py`).
        *   Envio de emails (notificações, cotações) (`email_tasks.py`).
        *   Geração de relatórios complexos (`report_tasks.py`).
        *   Sincronização com Google Calendar (`calendar_tasks.py`).
        *   Limpeza de sessões inativas (`session_tasks.py`).
*   **Redis (`app/core/config.py` para URL, `aioredis` para cliente):**
    *   Broker e Backend Celery.
    *   Cache de sessão (se não depender apenas da tabela `user_sessions` para validação rápida).
    *   Cache de queries frequentes (e.g., dados públicos, configurações de empresa).
    *   Rate limiting (usando `slowapi` ou implementação customizada).
    *   Filas para WebSockets (para desacoplar envio de mensagens da lógica principal).

### 9. Estratégia de Deploy (Docker + Docker Compose)

*   **Dockerfile (`backend/Dockerfile`):**
    ```dockerfile
    FROM python:3.11-slim

    WORKDIR /app

    # Variáveis de ambiente para não gerar .pyc e bufferizar output
    ENV PYTHONDONTWRITEBYTECODE 1
    ENV PYTHONUNBUFFERED 1

    # Instalar dependências do sistema (ex: build-essential para algumas libs, libpq-dev para psycopg2)
    RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        # Adicionar outras dependências se necessário (ex: para PyMuPDF)
        && apt-get clean && rm -rf /var/lib/apt/lists/*

    # Instalar Poetry (ou pip se preferir requirements.txt)
    RUN pip install poetry==1.7.1 # Ou versão mais recente

    COPY poetry.lock pyproject.toml /app/

    # Instalar dependências do projeto sem dev
    RUN poetry config virtualenvs.create false && \
        poetry install --no-dev --no-interaction --no-ansi

    COPY . /app/

    # Entrypoint para rodar migrações e iniciar app
    COPY ./docker-entrypoint.sh /docker-entrypoint.sh
    RUN chmod +x /docker-entrypoint.sh

    EXPOSE 8000

    ENTRYPOINT ["/docker-entrypoint.sh"]
    # CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] # Será chamado pelo entrypoint
    ```
*   **docker-entrypoint.sh:**
    ```bash
    #!/bin/sh
    set -e

    # Esperar pelo PostgreSQL (opcional, mas bom para dev)
    # while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
    #   echo "Waiting for Postgres..."
    #   sleep 1
    # done
    # echo "Postgres started"

    # Rodar migrações Alembic
    echo "Running database migrations..."
    alembic upgrade head

    # Iniciar a aplicação (passando quaisquer argumentos para o entrypoint)
    exec "$@"
    # Se o CMD no Dockerfile for usado, o exec "$@" pode ser substituído por:
    # exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 # Para produção, ou usar Gunicorn
    ```
    No Docker Compose, o `command` para o serviço backend seria: `sh -c "/docker-entrypoint.sh uvicorn app.main:app --host 0.0.0.0 --port 8000"` (ou com Gunicorn).

*   **docker-compose.yml (Simplificado):**
    ```yaml
    version: '3.8'

    services:
      backend:
        build: ./backend
        command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload # Para dev
        # command: sh -c "/docker-entrypoint.sh gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app -b 0.0.0.0:8000" # Para prod
        volumes:
          - ./backend:/app # Para dev com reload
        ports:
          - "8000:8000"
        env_file:
          - ./backend/.env
        depends_on:
          db_postgres:
            condition: service_healthy # PostgreSQL healthcheck
          db_mongo:
            condition: service_started # MongoDB healthcheck (verificar documentação)
          redis:
            condition: service_healthy # Redis healthcheck

      db_postgres:
        image: postgres:15-alpine
        volumes:
          - postgres_data:/var/lib/postgresql/data/
        ports:
          - "5432:5432"
        environment:
          - POSTGRES_USER=${POSTGRES_USER}
          - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
          - POSTGRES_DB=${POSTGRES_DB}
        healthcheck:
          test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
          interval: 10s
          timeout: 5s
          retries: 5

      db_mongo:
        image: mongo:6.0 # Ou mais recente estável
        volumes:
          - mongo_data:/data/db
        ports:
          - "27017:27017"
        environment:
          - MONGO_INITDB_ROOT_USERNAME=${MONGO_ROOT_USER}
          - MONGO_INITDB_ROOT_PASSWORD=${MONGO_ROOT_PASSWORD}
        # Adicionar healthcheck se disponível/necessário

      redis:
        image: redis:7-alpine
        ports:
          - "6379:6379"
        healthcheck:
          test: ["CMD", "redis-cli", "ping"]
          interval: 10s
          timeout: 5s
          retries: 5

      celery_worker:
        build: ./backend
        command: celery -A app.tasks.celery_app worker -l info
        volumes:
          - ./backend:/app
        env_file:
          - ./backend/.env
        depends_on:
          - redis
          - db_postgres # Se tarefas acessam o banco

      celery_beat:
        build: ./backend
        command: celery -A app.tasks.celery_app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler # Ou redbeat
        volumes:
          - ./backend:/app
        env_file:
          - ./backend/.env
        depends_on:
          - redis
          - db_postgres

      # Ollama (exemplo, pode variar dependendo de como você quer rodá-lo)
      ollama:
        image: ollama/ollama:latest # Verificar GPUs se necessário para produção
        ports:
          - "11434:11434"
        volumes:
          - ollama_data:/root/.ollama
        # tty: true # Para manter o container rodando
        # restart: always
        # deploy: # Para habilitar GPU
        #   resources:
        #     reservations:
        #       devices:
        #         - driver: nvidia
        #           count: 1
        #           capabilities: [gpu]

    volumes:
      postgres_data:
      mongo_data:
      ollama_data:
    ```
    **Nota:** O uso de GPU com Ollama em Docker requer configuração específica (NVIDIA Container Toolkit). Para desenvolvimento local, pode rodar na CPU.

### 9.1. Arquivo pyproject.toml Completo

```toml
[tool.poetry]
name = "licitacao-backend"
version = "0.1.0"
description = "Sistema de Automação de Licitações - Backend"
authors = ["Your Name <email@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.110.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
gunicorn = "^21.2.0"
sqlalchemy = "^2.0.25"
asyncpg = "^0.29.0"
alembic = "^1.13.1"
motor = "^3.3.2"
aioredis = "^2.0.1"
celery = "^5.3.4"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-multipart = "^0.0.6"
httpx = "^0.26.0"
pydantic = {extras = ["email"], version = "^2.5.0"}
pydantic-settings = "^2.1.0"
pymupdf = "^1.23.14"
python-docx = "^1.1.0"
slowapi = "^0.1.9"
redis = "^5.0.1"
emails = "^0.6"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.4"
pytest-asyncio = "^0.23.2"
pytest-cov = "^4.1.0"
black = "^23.12.1"
isort = "^5.13.2"
flake8 = "^6.1.0"
mypy = "^1.8.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --cov=app --cov-report=html --cov-report=term-missing"
```

### 10. Pontos Críticos e Sugestões de Melhorias

*   **Processamento de Editais:** A extração de dados de PDFs/DOCs diversos é complexa. A robustez do `_extract_text_from_file` e dos prompts de IA é crucial. Considerar bibliotecas especializadas e talvez até um serviço dedicado para OCR/parsing se Ollama/OpenAI não forem suficientes diretamente com o conteúdo bruto.
*   **Performance da IA:** Processamento local com Ollama pode ser lento dependendo do hardware. Para produção, OpenAI pode ser mais performático mas custoso. Avaliar trade-offs.
*   **"API Temporal":** A lógica de controle de sessão pode se tornar complexa. Testar exaustivamente. Manter o escopo gerenciável inicialmente.
*   **Migrações de Schema:** Alembic para PostgreSQL é fundamental. Para MongoDB, as migrações são mais manuais (scripts) ou via ferramentas de gerenciamento de schema NoSQL.
*   **Segurança de Uploads:** Validar tipos de arquivo, tamanhos, escanear por malware (ClamAV em um container separado, por exemplo).
*   **Escalabilidade de WebSockets:** Para muitos usuários, um único `ConnectionManager` pode não escalar. Considerar usar Redis Pub/Sub para distribuir mensagens entre múltiplas instâncias do backend.
*   **Testes:** Cobertura de testes >80% é um bom objetivo. Foco em testes de integração para fluxos críticos.
*   **Logging e Monitoramento:** Implementar logging estruturado (e.g., JSON). Para produção, integrar com ELK, Grafana/Prometheus. Sentry para rastreamento de erros.
*   **Configuração de Celery Beat:** O `django_celery_beat.schedulers:DatabaseScheduler` requer tabelas Django. Para uma abordagem pura FastAPI/SQLAlchemy, `celery-beat-alchemy` ou `redbeat` (Redis-backed) podem ser alternativas.

Este plano fornece uma base sólida. Detalhes específicos de implementação surgirão durante o desenvolvimento. O foco deve ser em construir iterativamente, testar continuamente e manter o código limpo e modularizado.