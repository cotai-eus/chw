# 🗄️ Plano Completo de Arquitetura de Banco de Dados

## 📋 Visão Geral da Arquitetura

### Stack de Dados Aprimorada
```
PostgreSQL (Principal) ── SQLAlchemy + asyncpg ── Dados relacionais críticos + AI metadata
MongoDB (NoSQL) ─────── Motor + AsyncIO ────── Dados flexíveis, notificações + AI logs
Redis (Cache/RT) ────── aioredis ──────────── Cache, sessões, real-time + AI cache
```

### 🚀 Novos Recursos Implementados
- **Sistema de IA Completo**: Processamento de documentos, prompts, monitoramento
- **Gestão Avançada de Sessões**: API Temporal com renovação automática
- **Rate Limiting Inteligente**: Controle por usuário, empresa e endpoint
- **Monitoramento Robusto**: Métricas de performance, saúde do sistema
- **Processamento Assíncrono**: Gestão completa de tarefas Celery
- **Auditoria Avançada**: Logs detalhados de IA e operações críticas
- **Cache Inteligente**: Cache de IA com invalidação automática

### Responsabilidades por Banco

#### 🔷 PostgreSQL - Dados Relacionais (SQLAlchemy + asyncpg)
- **Core Business**: Autenticação, usuários, empresas, permissões
- **Formulários**: Templates e submissões estruturadas
- **Sistema Kanban**: Boards, listas, cards e colaboração
- **Cotações**: Fornecedores, produtos, licitações e cotações
- **Calendário**: Eventos e agendamentos
- **🆕 Sistema de IA**: Processamento de documentos, prompts, monitoramento
- **🆕 Sessões Avançadas**: API Temporal com controle refinado
- **🆕 Rate Limiting**: Controle de acesso e throttling
- **🆕 Auditoria**: Logs detalhados e rastreamento
- **🆕 Tarefas Assíncronas**: Gestão de jobs Celery
- **🆕 Arquivos**: Sistema completo de upload e storage
- **🆕 Monitoramento**: Métricas de performance e saúde

#### 🟢 MongoDB - Dados Flexíveis (Motor)
- **Notificações**: Sistema completo multi-canal
- **Histórico**: Atividades detalhadas com contexto
- **Configurações**: Settings dinâmicos personalizáveis
- **Templates**: Layouts e automações flexíveis
- **🆕 AI Logs**: Logs detalhados de processamento de IA
- **🆕 Prompt History**: Histórico de prompts e respostas
- **🆕 Analytics**: Métricas avançadas e insights
- **🆕 Error Tracking**: Rastreamento detalhado de erros
- **🆕 Document Chunks**: Fragmentos de documentos para IA

#### 🔴 Redis - Cache e Real-time (aioredis)
- **Sessões**: TTL inteligente com renovação automática
- **Chat**: Mensagens real-time e presença online
- **Rate Limiting**: Contadores de requisições
- **🆕 AI Cache**: Cache inteligente de respostas de IA
- **🆕 Processing Queue**: Filas de processamento de documentos
- **🆕 Session Store**: Store avançado de sessões temporárias
- **🆕 Real-time Notifications**: Pub/Sub para notificações
- **🆕 Performance Cache**: Cache de queries e computações

---

## 🐘 POSTGRESQL - Esquema Relacional

### 1. Sistema de Autenticação e Usuários

```sql
-- Empresas/Organizações
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    cnpj VARCHAR(18) UNIQUE,
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    logo_url VARCHAR(500),
    
    -- Configurações de plano
    plan_type VARCHAR(50) DEFAULT 'BASIC', -- BASIC, PRO, ENTERPRISE
    max_users INTEGER DEFAULT 5,
    max_storage_gb INTEGER DEFAULT 10,
    features JSONB DEFAULT '{}', -- {"kanban": true, "chat": false}
    
    -- Configurações de empresa
    business_hours JSONB DEFAULT '{}', -- {"monday": {"start": "09:00", "end": "18:00"}}
    timezone VARCHAR(50) DEFAULT 'America/Sao_Paulo',
    
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, SUSPENDED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Usuários com hierarquia
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    -- Dados básicos
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(500),
    
    -- Hierarquia e permissões
    role VARCHAR(20) NOT NULL DEFAULT 'USER', -- MASTER, ADMIN, MANAGER, USER, VIEWER
    permissions JSONB DEFAULT '{}', -- {"forms": ["read", "write"], "kanban": ["read"]}
    
    -- Status e controle
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, PENDING, SUSPENDED
    email_verified BOOLEAN DEFAULT FALSE,
    must_change_password BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    last_login_at TIMESTAMP WITH TIME ZONE,
    password_changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT users_company_email_unique UNIQUE (company_id, email)
);

-- Perfis de usuário (dados adicionais)
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Informações pessoais
    bio TEXT,
    phone VARCHAR(20),
    department VARCHAR(100),
    position VARCHAR(100),
    location VARCHAR(255),
    birth_date DATE,
    
    -- Preferências do sistema
    language VARCHAR(10) DEFAULT 'pt-BR',
    theme VARCHAR(20) DEFAULT 'light', -- light, dark, auto
    notifications_email BOOLEAN DEFAULT TRUE,
    notifications_push BOOLEAN DEFAULT TRUE,
    notifications_desktop BOOLEAN DEFAULT TRUE,
    
    -- Configurações de trabalho
    working_hours JSONB DEFAULT '{}',
    calendar_integration JSONB DEFAULT '{}', -- Google, Outlook configs
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sessões de usuário (API Temporal) - APRIMORADO
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Token e identificação
    token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255),
    device_fingerprint VARCHAR(255),
    
    -- Informações da sessão
    ip_address INET,
    user_agent TEXT,
    device_type VARCHAR(20), -- desktop, mobile, tablet
    os_info VARCHAR(100),
    browser_info VARCHAR(100),
    location_data JSONB DEFAULT '{}', -- cidade, país, timezone
    
    -- Controle temporal aprimorado
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    max_idle_minutes INTEGER DEFAULT 30,
    auto_renew BOOLEAN DEFAULT TRUE,
    renewal_count INTEGER DEFAULT 0,
    max_renewals INTEGER DEFAULT 100,
    
    -- Controle de atividade
    activity_score INTEGER DEFAULT 100, -- Pontuação de atividade (0-100)
    suspicious_activity BOOLEAN DEFAULT FALSE,
    failed_requests INTEGER DEFAULT 0,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    force_logout BOOLEAN DEFAULT FALSE,
    logout_reason VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_renewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_user_sessions_user_id (user_id),
    INDEX idx_user_sessions_token (token_hash),
    INDEX idx_user_sessions_active (is_active, expires_at),
    INDEX idx_user_sessions_activity (last_activity DESC)
);

-- Atividades de sessão para monitoramento
CREATE TABLE session_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    
    -- Detalhes da atividade
    activity_type VARCHAR(50) NOT NULL, -- PAGE_VIEW, API_CALL, UPLOAD, etc
    endpoint VARCHAR(255),
    method VARCHAR(10),
    
    -- Métricas
    response_time_ms INTEGER,
    status_code INTEGER,
    bytes_transferred BIGINT DEFAULT 0,
    
    -- Contexto
    referrer VARCHAR(500),
    user_agent_changes BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_session_activities_session (session_id),
    INDEX idx_session_activities_created (created_at DESC),
    INDEX idx_session_activities_type (activity_type)
);
```

### 2. 🤖 Sistema de IA e Processamento de Documentos

```sql
-- Documentos para processamento de IA
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    
    -- Informações do arquivo
    original_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_hash VARCHAR(128) UNIQUE NOT NULL, -- SHA-256 para deduplicação
    
    -- Metadados
    document_type VARCHAR(50), -- TENDER, CONTRACT, INVOICE, etc
    language VARCHAR(10) DEFAULT 'pt-BR',
    page_count INTEGER,
    
    -- Status de processamento
    processing_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED, RETRY
    ai_confidence_score DECIMAL(5,4), -- 0.0000 a 1.0000
    
    -- Análise de qualidade
    quality_score INTEGER DEFAULT 0, -- 0-100
    has_text BOOLEAN DEFAULT FALSE,
    needs_ocr BOOLEAN DEFAULT FALSE,
    is_searchable BOOLEAN DEFAULT FALSE,
    
    -- Relacionamentos
    tender_id UUID REFERENCES tenders(id), -- Se relacionado a uma licitação
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_documents_company (company_id),
    INDEX idx_documents_user (uploaded_by),
    INDEX idx_documents_status (processing_status),
    INDEX idx_documents_hash (file_hash),
    INDEX idx_documents_tender (tender_id)
);

-- Processamento de IA detalhado
CREATE TABLE ai_processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Configuração do job
    job_type VARCHAR(50) NOT NULL, -- TEXT_EXTRACTION, TENDER_ANALYSIS, RISK_ASSESSMENT
    ai_model VARCHAR(100) NOT NULL, -- llama3-8b, gpt-4, etc
    prompt_template VARCHAR(100),
    
    -- Parâmetros de processamento
    processing_params JSONB DEFAULT '{}',
    chunk_size INTEGER DEFAULT 1000,
    overlap_size INTEGER DEFAULT 200,
    
    -- Status e progresso
    status VARCHAR(20) DEFAULT 'QUEUED', -- QUEUED, RUNNING, COMPLETED, FAILED, RETRYING
    progress_percentage INTEGER DEFAULT 0,
    current_step VARCHAR(100),
    
    -- Métricas de performance
    processing_time_ms BIGINT,
    tokens_used INTEGER DEFAULT 0,
    cost_estimate DECIMAL(10,6) DEFAULT 0.000000,
    
    -- Controle de retry
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    
    -- Prioridade e recursos
    priority INTEGER DEFAULT 5, -- 1-10 (10 = alta prioridade)
    gpu_required BOOLEAN DEFAULT FALSE,
    memory_mb_required INTEGER DEFAULT 512,
    
    -- Celery task info
    celery_task_id VARCHAR(255),
    worker_hostname VARCHAR(255),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_ai_jobs_document (document_id),
    INDEX idx_ai_jobs_status (status),
    INDEX idx_ai_jobs_created (created_at DESC),
    INDEX idx_ai_jobs_celery (celery_task_id)
);

-- Resultados de extração de texto
CREATE TABLE text_extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ai_job_id UUID REFERENCES ai_processing_jobs(id),
    
    -- Conteúdo extraído
    extracted_text TEXT NOT NULL,
    confidence_score DECIMAL(5,4) DEFAULT 1.0000,
    
    -- Metadados da extração
    extraction_method VARCHAR(20) NOT NULL, -- PDFPLUMBER, OCR, HYBRID
    ocr_engine VARCHAR(50), -- tesseract, paddleocr, etc
    
    -- Análise de qualidade
    text_quality_score INTEGER DEFAULT 0, -- 0-100
    has_tables BOOLEAN DEFAULT FALSE,
    has_images BOOLEAN DEFAULT FALSE,
    language_detected VARCHAR(10),
    
    -- Estrutura do documento
    sections JSONB DEFAULT '[]', -- Array de seções identificadas
    tables JSONB DEFAULT '[]', -- Tabelas extraídas
    metadata JSONB DEFAULT '{}', -- Metadados adicionais
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_text_extractions_document (document_id),
    INDEX idx_text_extractions_job (ai_job_id)
);

-- Análises de licitações (IA)
CREATE TABLE tender_ai_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id),
    ai_job_id UUID REFERENCES ai_processing_jobs(id),
    
    -- Análise principal
    analysis_type VARCHAR(50) NOT NULL, -- RISK_ASSESSMENT, ITEM_EXTRACTION, DEADLINE_ANALYSIS
    
    -- Pontuações e métricas
    overall_score INTEGER DEFAULT 0, -- 0-100
    risk_score INTEGER DEFAULT 0, -- 0-100
    complexity_score INTEGER DEFAULT 0, -- 0-100
    opportunity_score INTEGER DEFAULT 0, -- 0-100
    
    -- Fatores identificados
    risk_factors JSONB DEFAULT '[]',
    opportunities JSONB DEFAULT '[]',
    requirements JSONB DEFAULT '[]',
    deadlines JSONB DEFAULT '[]',
    
    -- Itens extraídos
    extracted_items JSONB DEFAULT '[]', -- Itens identificados pela IA
    categories JSONB DEFAULT '[]', -- Categorias identificadas
    
    -- Recomendações
    recommendations JSONB DEFAULT '[]',
    action_items JSONB DEFAULT '[]',
    
    -- Confiança e validação
    confidence_score DECIMAL(5,4) DEFAULT 0.0000,
    needs_human_review BOOLEAN DEFAULT TRUE,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_tender_ai_analyses_tender (tender_id),
    INDEX idx_tender_ai_analyses_document (document_id),
    INDEX idx_tender_ai_analyses_type (analysis_type),
    INDEX idx_tender_ai_analyses_score (overall_score DESC)
);

-- Templates de prompts para IA
CREATE TABLE ai_prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificação
    name VARCHAR(255) NOT NULL UNIQUE,
    version VARCHAR(20) DEFAULT '1.0.0',
    description TEXT,
    
    -- Configuração do prompt
    template_content TEXT NOT NULL, -- Template Jinja2
    category VARCHAR(50) NOT NULL, -- EXTRACTION, ANALYSIS, CLASSIFICATION
    use_case VARCHAR(100), -- TENDER_ANALYSIS, RISK_ASSESSMENT, etc
    
    -- Parâmetros
    default_parameters JSONB DEFAULT '{}',
    required_variables JSONB DEFAULT '[]',
    
    -- Configurações do modelo
    target_models JSONB DEFAULT '[]', -- ["llama3-8b", "gpt-4"]
    max_tokens INTEGER DEFAULT 4000,
    temperature DECIMAL(3,2) DEFAULT 0.30,
    
    -- Controle de qualidade
    quality_threshold DECIMAL(5,4) DEFAULT 0.8000,
    test_cases JSONB DEFAULT '[]',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_production BOOLEAN DEFAULT FALSE,
    
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_ai_prompts_category (category),
    INDEX idx_ai_prompts_use_case (use_case),
    INDEX idx_ai_prompts_active (is_active)
);

-- Cache de respostas de IA
CREATE TABLE ai_response_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Chave do cache
    cache_key VARCHAR(128) UNIQUE NOT NULL, -- Hash do prompt + parâmetros
    prompt_hash VARCHAR(128) NOT NULL,
    parameters_hash VARCHAR(128) NOT NULL,
    
    -- Conteúdo
    response_content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    
    -- Métricas
    confidence_score DECIMAL(5,4),
    tokens_used INTEGER,
    processing_time_ms BIGINT,
    
    -- Controle de cache
    hit_count INTEGER DEFAULT 0,
    last_hit_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Validação
    is_validated BOOLEAN DEFAULT FALSE,
    validation_score DECIMAL(5,4),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_ai_cache_key (cache_key),
    INDEX idx_ai_cache_prompt (prompt_hash),
    INDEX idx_ai_cache_expires (expires_at),
    INDEX idx_ai_cache_hits (hit_count DESC)
);
```

### 3. 🛡️ Sistema de Rate Limiting e Segurança

```sql
-- Rate limiting por usuário/empresa
CREATE TABLE rate_limit_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificação
    user_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    ip_address INET,
    endpoint_pattern VARCHAR(255) NOT NULL,
    
    -- Contadores
    requests_count INTEGER DEFAULT 1,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    window_duration_seconds INTEGER NOT NULL,
    
    -- Limites
    max_requests INTEGER NOT NULL,
    current_requests INTEGER DEFAULT 1,
    
    -- Status
    is_blocked BOOLEAN DEFAULT FALSE,
    blocked_until TIMESTAMP WITH TIME ZONE,
    
    -- Contexto
    user_agent TEXT,
    request_path VARCHAR(500),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_rate_limit_user (user_id),
    INDEX idx_rate_limit_company (company_id),
    INDEX idx_rate_limit_ip (ip_address),
    INDEX idx_rate_limit_window (window_start, endpoint_pattern),
    INDEX idx_rate_limit_blocked (is_blocked, blocked_until)
);

-- Eventos de segurança
CREATE TABLE security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificação
    user_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    session_id UUID REFERENCES user_sessions(id),
    
    -- Tipo de evento
    event_type VARCHAR(50) NOT NULL, -- SUSPICIOUS_LOGIN, RATE_LIMIT_EXCEEDED, etc
    severity VARCHAR(20) DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, CRITICAL
    
    -- Detalhes
    description TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    
    -- Contexto técnico
    ip_address INET,
    user_agent TEXT,
    endpoint VARCHAR(255),
    request_method VARCHAR(10),
    
    -- Resposta automática
    action_taken VARCHAR(100), -- BLOCKED, LOGGED, NOTIFICATION_SENT
    auto_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES users(id),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_security_events_user (user_id),
    INDEX idx_security_events_company (company_id),
    INDEX idx_security_events_type (event_type),
    INDEX idx_security_events_severity (severity),
    INDEX idx_security_events_created (created_at DESC)
);

-- Configurações de rate limiting
CREATE TABLE rate_limit_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Aplicabilidade
    company_id UUID REFERENCES companies(id), -- NULL = política global
    endpoint_pattern VARCHAR(255) NOT NULL,
    method VARCHAR(10) DEFAULT 'ALL', -- GET, POST, PUT, DELETE, ALL
    
    -- Configurações de limite
    requests_per_minute INTEGER DEFAULT 60,
    requests_per_hour INTEGER DEFAULT 1000,
    requests_per_day INTEGER DEFAULT 10000,
    
    -- Configurações por role
    role_limits JSONB DEFAULT '{}', -- {"ADMIN": {"per_minute": 120}, "USER": {"per_minute": 60}}
    
    -- Configurações avançadas
    burst_allowance INTEGER DEFAULT 10, -- Rajadas permitidas
    block_duration_minutes INTEGER DEFAULT 15,
    progressive_penalties BOOLEAN DEFAULT TRUE,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 5, -- 1-10 (10 = maior prioridade)
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_rate_policies_company (company_id),
    INDEX idx_rate_policies_endpoint (endpoint_pattern),
    INDEX idx_rate_policies_active (is_active)
);
```

### 4. 📊 Sistema de Monitoramento e Métricas

```sql
-- Métricas de performance de API
CREATE TABLE api_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificação da requisição
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    user_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    
    -- Métricas de performance
    response_time_ms INTEGER NOT NULL,
    db_query_time_ms INTEGER DEFAULT 0,
    ai_processing_time_ms INTEGER DEFAULT 0,
    cache_hit BOOLEAN DEFAULT FALSE,
    
    -- Status da requisição
    status_code INTEGER NOT NULL,
    success BOOLEAN DEFAULT TRUE,
    error_type VARCHAR(50),
    
    -- Contexto
    request_size_bytes INTEGER DEFAULT 0,
    response_size_bytes INTEGER DEFAULT 0,
    ip_address INET,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    date_only DATE GENERATED ALWAYS AS (created_at::DATE) STORED,
    hour_bucket TIMESTAMP GENERATED ALWAYS AS (date_trunc('hour', created_at)) STORED,
    
    INDEX idx_api_metrics_endpoint (endpoint),
    INDEX idx_api_metrics_user (user_id),
    INDEX idx_api_metrics_company (company_id),
    INDEX idx_api_metrics_date (date_only),
    INDEX idx_api_metrics_hour (hour_bucket),
    INDEX idx_api_metrics_performance (response_time_ms DESC)
);

-- Métricas de sistema
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Tipo de métrica
    metric_type VARCHAR(50) NOT NULL, -- CPU_USAGE, MEMORY_USAGE, DISK_USAGE, etc
    metric_name VARCHAR(100) NOT NULL,
    
    -- Valores
    value DECIMAL(10,4) NOT NULL,
    unit VARCHAR(20) NOT NULL, -- percent, bytes, seconds, etc
    
    -- Contexto
    hostname VARCHAR(255),
    service_name VARCHAR(100), -- api, celery, redis, postgres, etc
    component VARCHAR(100),
    
    -- Metadados
    metadata JSONB DEFAULT '{}',
    
    -- Alertas
    threshold_warning DECIMAL(10,4),
    threshold_critical DECIMAL(10,4),
    alert_triggered BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    date_only DATE GENERATED ALWAYS AS (created_at::DATE) STORED,
    minute_bucket TIMESTAMP GENERATED ALWAYS AS (date_trunc('minute', created_at)) STORED,
    
    INDEX idx_system_metrics_type (metric_type),
    INDEX idx_system_metrics_service (service_name),
    INDEX idx_system_metrics_date (date_only),
    INDEX idx_system_metrics_minute (minute_bucket),
    INDEX idx_system_metrics_alert (alert_triggered, created_at DESC)
);

-- Saúde dos serviços
CREATE TABLE service_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificação do serviço
    service_name VARCHAR(100) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    version VARCHAR(50),
    
    -- Status de saúde
    status VARCHAR(20) NOT NULL, -- HEALTHY, DEGRADED, UNHEALTHY, DOWN
    last_check TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Métricas de saúde
    uptime_seconds BIGINT DEFAULT 0,
    response_time_ms INTEGER,
    error_rate DECIMAL(5,4) DEFAULT 0.0000,
    
    -- Detalhes
    dependencies_status JSONB DEFAULT '{}', -- Status de dependências
    health_details JSONB DEFAULT '{}',
    error_messages TEXT[],
    
    -- Configurações de check
    check_interval_seconds INTEGER DEFAULT 30,
    timeout_seconds INTEGER DEFAULT 10,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_service_health_service (service_name),
    INDEX idx_service_health_status (status),
    INDEX idx_service_health_check (last_check DESC),
    
    CONSTRAINT service_health_hostname_service_unique UNIQUE (hostname, service_name)
);
```

### 5. 📁 Sistema de Arquivos e Storage

```sql
-- Arquivos do sistema
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    
    -- Informações básicas
    original_name VARCHAR(500) NOT NULL,
    display_name VARCHAR(500),
    file_path VARCHAR(1000) NOT NULL,
    storage_type VARCHAR(20) DEFAULT 'LOCAL', -- LOCAL, S3, AZURE, GCS
    
    -- Metadados do arquivo
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_hash VARCHAR(128) NOT NULL,
    
    -- Classificação
    category VARCHAR(50), -- DOCUMENT, IMAGE, VIDEO, AUDIO, OTHER
    tags TEXT[],
    description TEXT,
    
    -- Controle de acesso
    visibility VARCHAR(20) DEFAULT 'PRIVATE', -- PUBLIC, PRIVATE, COMPANY, TEAM
    access_permissions JSONB DEFAULT '{}',
    
    -- Relacionamentos
    tender_id UUID REFERENCES tenders(id),
    kanban_card_id UUID REFERENCES kanban_cards(id),
    form_submission_id UUID REFERENCES form_submissions(id),
    
    -- Processamento
    requires_processing BOOLEAN DEFAULT FALSE,
    processing_status VARCHAR(20) DEFAULT 'NOT_REQUIRED',
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Versionamento
    version INTEGER DEFAULT 1,
    parent_file_id UUID REFERENCES files(id),
    is_latest_version BOOLEAN DEFAULT TRUE,
    
    -- Lifecycle
    expires_at TIMESTAMP WITH TIME ZONE,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_files_company (company_id),
    INDEX idx_files_user (uploaded_by),
    INDEX idx_files_hash (file_hash),
    INDEX idx_files_tender (tender_id),
    INDEX idx_files_card (kanban_card_id),
    INDEX idx_files_category (category),
    INDEX idx_files_processing (processing_status)
);

-- Download e access logs
CREATE TABLE file_access_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    
    -- Tipo de acesso
    access_type VARCHAR(20) NOT NULL, -- DOWNLOAD, VIEW, PREVIEW, THUMBNAIL
    
    -- Contexto técnico
    ip_address INET,
    user_agent TEXT,
    referrer VARCHAR(500),
    
    -- Resultado
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    bytes_transferred BIGINT DEFAULT 0,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_file_access_file (file_id),
    INDEX idx_file_access_user (user_id),
    INDEX idx_file_access_created (created_at DESC)
);
```

### 6. 🔄 Sistema de Tarefas Assíncronas (Celery)

```sql
-- Jobs do Celery
CREATE TABLE celery_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificação Celery
    celery_task_id VARCHAR(255) UNIQUE NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    
    -- Contexto de usuário
    user_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    
    -- Parâmetros e configuração
    task_args JSONB DEFAULT '[]',
    task_kwargs JSONB DEFAULT '{}',
    
    -- Status e progresso
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, STARTED, RETRY, SUCCESS, FAILURE, REVOKED
    progress_percentage INTEGER DEFAULT 0,
    current_step VARCHAR(200),
    
    -- Resultado e erro
    result JSONB,
    error_message TEXT,
    traceback TEXT,
    
    -- Retry e controle
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Recursos utilizados
    worker_hostname VARCHAR(255),
    queue_name VARCHAR(100) DEFAULT 'default',
    priority INTEGER DEFAULT 5,
    
    -- Métricas
    eta TIMESTAMP WITH TIME ZONE,
    runtime_seconds DECIMAL(10,3),
    memory_usage_mb INTEGER,
    
    -- Relacionamentos
    parent_task_id UUID REFERENCES celery_tasks(id),
    related_entity_type VARCHAR(50), -- DOCUMENT, TENDER, AI_JOB
    related_entity_id UUID,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_celery_tasks_celery_id (celery_task_id),
    INDEX idx_celery_tasks_user (user_id),
    INDEX idx_celery_tasks_company (company_id),
    INDEX idx_celery_tasks_status (status),
    INDEX idx_celery_tasks_created (created_at DESC),
    INDEX idx_celery_tasks_queue (queue_name, priority DESC)
);

-- Monitoramento de workers
CREATE TABLE celery_workers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificação
    hostname VARCHAR(255) NOT NULL,
    worker_name VARCHAR(255) NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'ONLINE', -- ONLINE, OFFLINE, BUSY, MAINTENANCE
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Capacidades
    queues TEXT[] DEFAULT '{"default"}',
    max_concurrency INTEGER DEFAULT 4,
    current_load INTEGER DEFAULT 0,
    
    -- Métricas
    tasks_processed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    average_runtime_seconds DECIMAL(10,3),
    
    -- Recursos do sistema
    cpu_usage DECIMAL(5,2),
    memory_usage_mb INTEGER,
    
    -- Configuração
    worker_config JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_celery_workers_hostname (hostname),
    INDEX idx_celery_workers_status (status),
    INDEX idx_celery_workers_heartbeat (last_heartbeat DESC),
    
    CONSTRAINT celery_workers_hostname_name_unique UNIQUE (hostname, worker_name)
);
```

### 7. 🚨 Logs de Auditoria Aprimorados

```sql
-- Templates de formulários
CREATE TABLE form_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100), -- survey, feedback, application, etc
    
    -- Estrutura do formulário
    schema JSONB NOT NULL, -- Campos, validações, configurações
    settings JSONB DEFAULT '{}', -- Cores, logos, configurações visuais
    
    -- Controle de acesso
    is_public BOOLEAN DEFAULT FALSE,
    requires_auth BOOLEAN DEFAULT TRUE,
    allowed_domains TEXT[], -- Domínios permitidos para submissão
    
    -- Configurações de submissão
    max_submissions INTEGER,
    submission_deadline TIMESTAMP WITH TIME ZONE,
    auto_close BOOLEAN DEFAULT FALSE,
    
    status VARCHAR(20) DEFAULT 'DRAFT', -- DRAFT, PUBLISHED, CLOSED, ARCHIVED
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT form_templates_company_name_unique UNIQUE (company_id, name)
);

-- Instâncias de formulários (quando enviados)
CREATE TABLE form_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES form_templates(id) ON DELETE CASCADE,
    
    -- Dados da submissão
    data JSONB NOT NULL, -- Respostas do formulário
    metadata JSONB DEFAULT '{}', -- IP, user-agent, tempo de preenchimento
    
    -- Identificação do respondente
    submitted_by UUID REFERENCES users(id), -- NULL se anônimo
    submitter_email VARCHAR(255),
    submitter_name VARCHAR(255),
    
    -- Status e processamento
    status VARCHAR(20) DEFAULT 'SUBMITTED', -- SUBMITTED, REVIEWED, APPROVED, REJECTED
    score DECIMAL(5,2), -- Para formulários com pontuação
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by UUID REFERENCES users(id),
    
    INDEX idx_form_submissions_template (template_id),
    INDEX idx_form_submissions_user (submitted_by),
    INDEX idx_form_submissions_status (status)
);
```

### 3. Sistema Kanban

```sql
-- Boards do Kanban
CREATE TABLE kanban_boards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3498db', -- Hex color
    icon VARCHAR(50), -- Icon identifier
    
    -- Configurações do board
    settings JSONB DEFAULT '{}', -- Customizações, automações
    visibility VARCHAR(20) DEFAULT 'TEAM', -- PRIVATE, TEAM, COMPANY
    
    -- Ordenação e status
    position INTEGER DEFAULT 0,
    is_archived BOOLEAN DEFAULT FALSE,
    
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT kanban_boards_company_name_unique UNIQUE (company_id, name)
);

-- Listas dentro dos boards
CREATE TABLE kanban_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id UUID NOT NULL REFERENCES kanban_boards(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    color VARCHAR(7),
    position INTEGER NOT NULL DEFAULT 0,
    
    -- Configurações da lista
    card_limit INTEGER, -- Limite de cards na lista
    is_done_list BOOLEAN DEFAULT FALSE, -- Lista de "concluído"
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT kanban_lists_board_name_unique UNIQUE (board_id, name)
);

-- Cards do Kanban
CREATE TABLE kanban_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    list_id UUID NOT NULL REFERENCES kanban_lists(id) ON DELETE CASCADE,
    
    title VARCHAR(500) NOT NULL,
    description TEXT,
    position INTEGER NOT NULL DEFAULT 0,
    
    -- Atribuição e datas
    assigned_to UUID REFERENCES users(id),
    due_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Classificação
    priority VARCHAR(10) DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, URGENT
    labels TEXT[], -- Array de labels/tags
    color VARCHAR(7),
    
    -- Estimativas e tracking
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    story_points INTEGER,
    
    -- Anexos e links
    attachments JSONB DEFAULT '[]', -- URLs de arquivos
    external_links JSONB DEFAULT '[]',
    
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_kanban_cards_list (list_id),
    INDEX idx_kanban_cards_assigned (assigned_to),
    INDEX idx_kanban_cards_due_date (due_date)
);

-- Comentários nos cards
CREATE TABLE kanban_card_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID NOT NULL REFERENCES kanban_cards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    content TEXT NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_card_comments_card (card_id),
    INDEX idx_card_comments_user (user_id)
);

-- Membros dos boards
CREATE TABLE kanban_board_members (
    board_id UUID NOT NULL REFERENCES kanban_boards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'MEMBER', -- OWNER, ADMIN, MEMBER, VIEWER
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (board_id, user_id)
);
```

### 4. Sistema de Cotações (baseado no documento)

```sql
-- Fornecedores
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18),
    email VARCHAR(255),
    phone VARCHAR(20),
    contact_person VARCHAR(255),
    
    -- Endereço
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(10),
    
    -- Informações comerciais
    lead_time_days INTEGER DEFAULT 0,
    payment_terms TEXT,
    commercial_conditions TEXT,
    
    -- Avaliação
    rating DECIMAL(3,2) DEFAULT 0.00, -- 0.00 a 5.00
    total_quotes INTEGER DEFAULT 0,
    successful_quotes INTEGER DEFAULT 0,
    
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT suppliers_company_cnpj_unique UNIQUE (company_id, cnpj)
);

-- Produtos/Serviços
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    unit VARCHAR(20) DEFAULT 'UN', -- Unidade de medida
    
    -- Classificação
    ncm_code VARCHAR(20), -- Código NCM
    tags TEXT[],
    
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Associação fornecedor-produto com preços
CREATE TABLE supplier_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    
    unit_price DECIMAL(12,2) NOT NULL,
    minimum_quantity INTEGER DEFAULT 1,
    lead_time_days INTEGER DEFAULT 0,
    
    -- Validade do preço
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_until DATE,
    
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT supplier_products_unique UNIQUE (supplier_id, product_id)
);

-- Editais/Licitações - APRIMORADO COM IA
CREATE TABLE tenders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    number VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    
    -- Prazos
    opening_date TIMESTAMP WITH TIME ZONE,
    submission_deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- IA e análise de risco APRIMORADO
    ai_processing_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, FAILED
    risk_score INTEGER DEFAULT 0, -- 0-100
    opportunity_score INTEGER DEFAULT 0, -- 0-100
    complexity_score INTEGER DEFAULT 0, -- 0-100
    
    -- Fatores identificados pela IA
    risk_factors JSONB DEFAULT '[]',
    opportunities JSONB DEFAULT '[]',
    technical_requirements JSONB DEFAULT '[]',
    legal_requirements JSONB DEFAULT '[]',
    
    -- Análise detalhada
    ai_analysis JSONB DEFAULT '{}',
    ai_confidence DECIMAL(5,4) DEFAULT 0.0000,
    ai_model_used VARCHAR(100),
    ai_analysis_date TIMESTAMP WITH TIME ZONE,
    
    -- Recomendações da IA
    ai_recommendations JSONB DEFAULT '[]',
    estimated_preparation_time INTEGER, -- em horas
    recommended_team_size INTEGER,
    
    -- Arquivos e processamento
    original_file_path VARCHAR(500),
    processed_data JSONB DEFAULT '{}',
    extraction_confidence DECIMAL(5,4),
    
    -- Monitoramento
    view_count INTEGER DEFAULT 0,
    bookmark_count INTEGER DEFAULT 0,
    last_viewed_at TIMESTAMP WITH TIME ZONE,
    
    status VARCHAR(20) DEFAULT 'DRAFT', -- DRAFT, ANALYZING, READY, QUOTED, SUBMITTED, WON, LOST
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT tenders_company_number_unique UNIQUE (company_id, number),
    
    INDEX idx_tenders_ai_status (ai_processing_status),
    INDEX idx_tenders_risk_score (risk_score DESC),
    INDEX idx_tenders_opportunity (opportunity_score DESC),
    INDEX idx_tenders_deadline (submission_deadline),
    INDEX idx_tenders_status (status)
);

-- Itens do edital
CREATE TABLE tender_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    
    item_number INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit VARCHAR(20) NOT NULL,
    specifications TEXT,
    
    -- Produto relacionado (se identificado)
    product_id UUID REFERENCES products(id),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT tender_items_unique UNIQUE (tender_id, item_number)
);

-- Cotações
CREATE TABLE quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    
    quote_number VARCHAR(100) NOT NULL,
    
    -- Status e envio
    status VARCHAR(20) DEFAULT 'DRAFT', -- DRAFT, SENT, RESPONDED, EXPIRED
    sent_at TIMESTAMP WITH TIME ZONE,
    response_deadline TIMESTAMP WITH TIME ZONE,
    
    -- Valores consolidados
    total_value DECIMAL(15,2) DEFAULT 0.00,
    discount_percentage DECIMAL(5,2) DEFAULT 0.00,
    final_value DECIMAL(15,2) DEFAULT 0.00,
    
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT quotes_company_number_unique UNIQUE (tender_id, quote_number)
);

-- Itens da cotação com fornecedores
CREATE TABLE quote_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    tender_item_id UUID NOT NULL REFERENCES tender_items(id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    
    unit_price DECIMAL(12,2) NOT NULL,
    total_price DECIMAL(15,2) NOT NULL,
    delivery_time_days INTEGER DEFAULT 0,
    
    -- Resposta do fornecedor
    supplier_response JSONB DEFAULT '{}',
    responded_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT quote_items_unique UNIQUE (quote_id, tender_item_id, supplier_id)
);
```

### 5. Sistema de Calendário

```sql
-- Calendários
CREATE TABLE calendars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3498db',
    
    -- Configurações
    is_public BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50) DEFAULT 'America/Sao_Paulo',
    
    -- Integração externa
    external_calendar_id VARCHAR(255), -- Google Calendar ID
    sync_enabled BOOLEAN DEFAULT FALSE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT calendars_owner_name_unique UNIQUE (owner_id, name)
);

-- Eventos
CREATE TABLE calendar_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID NOT NULL REFERENCES calendars(id) ON DELETE CASCADE,
    
    title VARCHAR(500) NOT NULL,
    description TEXT,
    location VARCHAR(255),
    
    -- Data e hora
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    is_all_day BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50),
    
    -- Recorrência
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_rule TEXT, -- RRULE format
    recurrence_end_date TIMESTAMP WITH TIME ZONE,
    
    -- Relacionamentos
    tender_id UUID REFERENCES tenders(id), -- Evento relacionado a licitação
    kanban_card_id UUID REFERENCES kanban_cards(id), -- Evento relacionado a card
    
    -- Configurações
    reminder_minutes INTEGER[], -- [15, 60] = lembretes em 15min e 1h antes
    is_private BOOLEAN DEFAULT FALSE,
    
    -- Integração externa
    external_event_id VARCHAR(255), -- Google Calendar Event ID
    
    status VARCHAR(20) DEFAULT 'CONFIRMED', -- TENTATIVE, CONFIRMED, CANCELLED
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_calendar_events_start_time (start_time),
    INDEX idx_calendar_events_calendar (calendar_id),
    INDEX idx_calendar_events_tender (tender_id)
);

-- Participantes dos eventos
CREATE TABLE event_attendees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES calendar_events(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    
    -- Para convidados externos
    email VARCHAR(255),
    name VARCHAR(255),
    
    response_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, ACCEPTED, DECLINED, TENTATIVE
    responded_at TIMESTAMP WITH TIME ZONE,
    
    is_organizer BOOLEAN DEFAULT FALSE,
    can_modify BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT event_attendees_unique UNIQUE (event_id, user_id, email)
);
```

### 6. Sistema de Mensagens (Metadados)

```sql
-- Conversas/Chats
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    
    name VARCHAR(255), -- Para grupos, NULL para conversas diretas
    type VARCHAR(20) DEFAULT 'DIRECT', -- DIRECT, GROUP, CHANNEL
    
    -- Relacionamentos opcionais
    kanban_card_id UUID REFERENCES kanban_cards(id), -- Chat de um card
    tender_id UUID REFERENCES tenders(id), -- Chat de uma licitação
    
    -- Configurações
    is_archived BOOLEAN DEFAULT FALSE,
    
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_conversations_company (company_id),
    INDEX idx_conversations_card (kanban_card_id),
    INDEX idx_conversations_tender (tender_id)
);

-- Participantes das conversas
CREATE TABLE conversation_participants (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    role VARCHAR(20) DEFAULT 'MEMBER', -- ADMIN, MEMBER
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_read_at TIMESTAMP WITH TIME ZONE,
    
    -- Configurações individuais
    notifications_enabled BOOLEAN DEFAULT TRUE,
    is_muted BOOLEAN DEFAULT FALSE,
    
    PRIMARY KEY (conversation_id, user_id)
);

-- Mensagens (apenas metadados, conteúdo no Redis/MongoDB)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    message_type VARCHAR(20) DEFAULT 'TEXT', -- TEXT, FILE, IMAGE, SYSTEM
    
    -- Referências
    reply_to_id UUID REFERENCES messages(id), -- Para respostas
    
    -- Status
    is_edited BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_messages_conversation (conversation_id),
    INDEX idx_messages_sender (sender_id),
    INDEX idx_messages_created (created_at DESC)
);
```

### 7. 🚨 Logs de Auditoria Aprimorados

```sql
-- Logs de auditoria APRIMORADOS
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificação
    user_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    session_id UUID REFERENCES user_sessions(id),
    
    -- Ação realizada
    action VARCHAR(100) NOT NULL, -- CREATE, UPDATE, DELETE, LOGIN, LOGOUT, AI_PROCESS
    entity_type VARCHAR(50) NOT NULL, -- USER, FORM, KANBAN_CARD, TENDER, AI_JOB, etc
    entity_id UUID,
    entity_name VARCHAR(500),
    
    -- Detalhes da mudança APRIMORADOS
    old_values JSONB,
    new_values JSONB,
    changes_summary TEXT,
    affected_fields TEXT[],
    
    -- Contexto técnico
    ip_address INET,
    user_agent TEXT,
    endpoint VARCHAR(255),
    request_method VARCHAR(10),
    request_id VARCHAR(255), -- Para correlação de logs
    
    -- Dados de performance
    processing_time_ms INTEGER,
    db_queries_count INTEGER DEFAULT 0,
    
    -- Classificação APRIMORADA
    severity VARCHAR(20) DEFAULT 'INFO', -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    category VARCHAR(50), -- SECURITY, DATA, SYSTEM, USER_ACTION, AI_OPERATION
    subcategory VARCHAR(100), -- LOGIN_SUCCESS, PASSWORD_CHANGE, AI_ANALYSIS_COMPLETE
    
    -- Contexto de negócio
    business_impact VARCHAR(20), -- LOW, MEDIUM, HIGH, CRITICAL
    compliance_relevant BOOLEAN DEFAULT FALSE,
    
    -- Geolocalização e dispositivo
    country_code VARCHAR(3),
    region VARCHAR(100),
    device_fingerprint VARCHAR(255),
    
    -- Alertas e monitoramento
    alert_generated BOOLEAN DEFAULT FALSE,
    alert_level VARCHAR(20),
    requires_review BOOLEAN DEFAULT FALSE,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    date_only DATE GENERATED ALWAYS AS (created_at::DATE) STORED,
    
    INDEX idx_audit_logs_user (user_id),
    INDEX idx_audit_logs_company (company_id),
    INDEX idx_audit_logs_entity (entity_type, entity_id),
    INDEX idx_audit_logs_created (created_at DESC),
    INDEX idx_audit_logs_action (action),
    INDEX idx_audit_logs_category (category, subcategory),
    INDEX idx_audit_logs_severity (severity),
    INDEX idx_audit_logs_date (date_only),
    INDEX idx_audit_logs_review (requires_review, reviewed_at)
);

-- Alertas e notificações de segurança
CREATE TABLE security_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Classificação do alerta
    alert_type VARCHAR(50) NOT NULL, -- BRUTE_FORCE, ANOMALY, BREACH_ATTEMPT
    severity VARCHAR(20) NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    priority INTEGER DEFAULT 5, -- 1-10
    
    -- Contexto
    company_id UUID REFERENCES companies(id),
    user_id UUID REFERENCES users(id),
    related_audit_log_ids UUID[], -- IDs de logs relacionados
    
    -- Detalhes
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    evidence JSONB DEFAULT '{}',
    
    -- Detecção
    detection_rule VARCHAR(255),
    confidence_score DECIMAL(5,4) DEFAULT 1.0000,
    false_positive_likelihood DECIMAL(5,4) DEFAULT 0.0000,
    
    -- Resposta
    status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, INVESTIGATING, RESOLVED, FALSE_POSITIVE
    assigned_to UUID REFERENCES users(id),
    resolution_notes TEXT,
    
    -- Ações automáticas
    auto_actions_taken JSONB DEFAULT '[]',
    manual_actions_required JSONB DEFAULT '[]',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_security_alerts_type (alert_type),
    INDEX idx_security_alerts_severity (severity),
    INDEX idx_security_alerts_company (company_id),
    INDEX idx_security_alerts_status (status),
    INDEX idx_security_alerts_created (created_at DESC)
);
```

---

## 🍃 MONGODB APRIMORADO - Dados Flexíveis

### Estrutura de Coleções Aprimoradas

```javascript
// 🤖 AI Processing Logs (NOVO)
ai_processing_logs: {
  _id: ObjectId,
  job_id: "uuid", // Referência para ai_processing_jobs
  document_id: "uuid",
  user_id: "uuid",
  company_id: "uuid",
  
  // Detalhes do processamento
  job_type: "TEXT_EXTRACTION", // TEXT_EXTRACTION, TENDER_ANALYSIS, etc
  model_used: "llama3-8b-instruct",
  
  // Timeline de processamento
  processing_steps: [
    {
      step: "document_loading",
      started_at: ISODate(),
      completed_at: ISODate(),
      duration_ms: 1250,
      success: true,
      details: { pages_loaded: 15, file_size_mb: 2.5 }
    },
    {
      step: "text_extraction",
      started_at: ISODate(),
      completed_at: ISODate(),
      duration_ms: 8750,
      success: true,
      details: { chars_extracted: 45230, confidence: 0.95 }
    },
    {
      step: "ai_analysis",
      started_at: ISODate(),
      completed_at: ISODate(),
      duration_ms: 15400,
      success: true,
      details: { tokens_used: 4850, temperature: 0.3 }
    }
  ],
  
  // Resultados e métricas
  results: {
    confidence_score: 0.87,
    tokens_used: 4850,
    cost_usd: 0.0485,
    processing_time_total_ms: 25400,
    quality_metrics: {
      text_clarity: 0.92,
      structure_detected: true,
      language_confidence: 0.98
    }
  },
  
  // Debugging e troubleshooting
  debug_info: {
    memory_usage_mb: 512,
    gpu_used: true,
    worker_hostname: "ai-worker-01",
    model_version: "3.1-8b-instruct-q4_0"
  },
  
  // Status e erros
  status: "COMPLETED", // STARTED, PROCESSING, COMPLETED, FAILED
  error_details: null,
  
  created_at: ISODate(),
  completed_at: ISODate()
}

// 📊 AI Model Performance Metrics (NOVO)
ai_model_metrics: {
  _id: ObjectId,
  
  // Identificação do modelo
  model_name: "llama3-8b-instruct",
  model_version: "3.1-q4_0",
  task_type: "TENDER_ANALYSIS",
  
  // Métricas de performance
  metrics: {
    average_response_time_ms: 12500,
    average_tokens_per_second: 45.2,
    success_rate: 0.94,
    confidence_scores: {
      average: 0.87,
      median: 0.89,
      std_deviation: 0.12
    },
    cost_metrics: {
      average_cost_per_request: 0.035,
      total_tokens_processed: 125000,
      total_cost_usd: 4.375
    }
  },
  
  // Análise de qualidade
  quality_analysis: {
    accuracy_samples: [
      {
        input_hash: "abc123...",
        expected_output: {...},
        actual_output: {...},
        similarity_score: 0.92,
        human_validated: true
      }
    ],
    common_errors: [
      {
        error_type: "date_extraction",
        frequency: 8,
        description: "Dificuldade em extrair datas em formato brasileiro"
      }
    ]
  },
  
  // Período de análise
  period_start: ISODate(),
  period_end: ISODate(),
  sample_size: 150,
  
  created_at: ISODate()
}

// 📋 Prompt History and Templates (NOVO)
prompt_history: {
  _id: ObjectId,
  
  // Identificação
  prompt_template_id: "uuid",
  execution_id: "uuid",
  user_id: "uuid",
  company_id: "uuid",
  
  // Prompt usado
  prompt_content: "Analise o seguinte edital de licitação...",
  variables_used: {
    tender_text: "Texto do edital...",
    company_context: "Empresa focada em TI...",
    analysis_type: "risk_assessment"
  },
  
  // Configurações do modelo
  model_config: {
    model: "llama3-8b-instruct",
    temperature: 0.3,
    max_tokens: 4000,
    top_p: 0.9,
    frequency_penalty: 0.1
  },
  
  // Resposta e métricas
  response: {
    content: "Análise detalhada do edital...",
    tokens_used: 3850,
    processing_time_ms: 12400,
    confidence_score: 0.89
  },
  
  // Avaliação e feedback
  evaluation: {
    human_rating: 4.5, // 1-5
    feedback: "Análise precisa, mas poderia incluir mais detalhes sobre prazos",
    validated_by: "uuid",
    validation_date: ISODate()
  },
  
  created_at: ISODate()
}

// 🔄 Document Processing Status (NOVO)
document_processing_status: {
  _id: ObjectId,
  document_id: "uuid",
  company_id: "uuid",
  
  // Pipeline de processamento
  processing_pipeline: [
    {
      stage: "upload_validation",
      status: "COMPLETED",
      started_at: ISODate(),
      completed_at: ISODate(),
      result: { valid: true, file_type: "pdf", size_mb: 2.3 }
    },
    {
      stage: "text_extraction",
      status: "COMPLETED", 
      started_at: ISODate(),
      completed_at: ISODate(),
      result: { 
        method: "pdfplumber",
        chars_extracted: 45230,
        pages_processed: 15,
        confidence: 0.95
      }
    },
    {
      stage: "ai_analysis",
      status: "IN_PROGRESS",
      started_at: ISODate(),
      progress: 0.65,
      current_step: "risk_assessment"
    }
  ],
  
  // Status consolidado
  overall_status: "PROCESSING", // QUEUED, PROCESSING, COMPLETED, FAILED
  progress_percentage: 65,
  estimated_completion: ISODate(),
  
  // Resultados parciais
  partial_results: {
    text_extraction: {
      preview: "Primeiro parágrafo do documento...",
      word_count: 8945,
      language: "pt-BR"
    }
  },
  
  // Erros e retry
  errors: [],
  retry_count: 0,
  
  created_at: ISODate(),
  updated_at: ISODate()
}

// 📱 Notificações APRIMORADAS
notifications: {
  _id: ObjectId,
  user_id: "uuid",
  company_id: "uuid",
  
  // Conteúdo da notificação APRIMORADO
  title: "Análise de IA concluída",
  message: "A análise do edital #2024-001 foi concluída com 87% de confiança",
  type: "AI_ANALYSIS_COMPLETE", // Novos tipos para IA
  category: "AI_PROCESSING", // TENDER, KANBAN, FORM, CALENDAR, SYSTEM, AI_PROCESSING
  
  // Dados estruturados APRIMORADOS
  data: {
    tender_id: "uuid",
    document_id: "uuid",
    analysis_type: "risk_assessment",
    confidence_score: 0.87,
    risk_score: 75,
    action_url: "/tenders/uuid/analysis",
    
    // Rich content para UI
    rich_content: {
      icon: "🤖",
      color: "#28a745",
      progress: 100,
      metrics: {
        "Pontuação de Risco": "75/100",
        "Confiança": "87%",
        "Tempo de Processamento": "2.5 min"
      }
    }
  },
  
  // Configurações de entrega APRIMORADAS
  delivery_config: {
    channels: ["push", "system"], // Não enviar por email para notifs de IA
    priority: "MEDIUM",
    batch_group: "ai_processing", // Para agrupar notificações similares
    auto_expire_hours: 72
  },
  
  // Status de entrega
  delivery_status: {
    push: { status: "DELIVERED", delivered_at: ISODate() },
    system: { status: "READ", read_at: ISODate() }
  },
  
  // Personalização
  personalization: {
    locale: "pt-BR",
    timezone: "America/Sao_Paulo",
    user_preferences: ["ai_notifications"]
  },
  
  created_at: ISODate(),
  updated_at: ISODate()
}

// 📈 Advanced Analytics (NOVO)
advanced_analytics: {
  _id: ObjectId,
  company_id: "uuid",
  
  // Tipo de análise
  analysis_type: "TENDER_PERFORMANCE", // TENDER_PERFORMANCE, AI_USAGE, USER_BEHAVIOR
  period: {
    start_date: ISODate(),
    end_date: ISODate(),
    granularity: "daily" // hourly, daily, weekly, monthly
  },
  
  // Métricas calculadas
  metrics: {
    tenders_analyzed: 45,
    avg_processing_time_min: 3.2,
    success_rate: 0.94,
    cost_efficiency: {
      total_cost_usd: 125.50,
      cost_per_tender: 2.79,
      cost_trend: "decreasing"
    },
    
    // Métricas de qualidade
    quality_metrics: {
      avg_confidence_score: 0.87,
      human_validation_rate: 0.15, // % que precisou de validação humana
      error_rate: 0.06
    },
    
    // Breakdown por categoria
    category_breakdown: {
      "technology": { count: 18, avg_risk: 65, success_rate: 0.96 },
      "construction": { count: 12, avg_risk: 78, success_rate: 0.88 },
      "services": { count: 15, avg_risk: 58, success_rate: 0.98 }
    }
  },
  
  // Insights automáticos
  ai_insights: [
    {
      type: "TREND",
      description: "Melhoria de 15% na precisão de análise de risco nos últimos 30 dias",
      confidence: 0.92,
      recommendation: "Considere aumentar o uso do sistema para licitações de maior valor"
    }
  ],
  
  // Dados para visualização
  chart_data: {
    processing_times: [2.1, 2.8, 3.2, 2.9, 3.1], // por dia
    success_rates: [0.91, 0.93, 0.94, 0.96, 0.94],
    cost_trends: [3.20, 2.95, 2.79, 2.81, 2.75]
  },
  
  created_at: ISODate()
}
```

---

## 🔴 REDIS APRIMORADO - Cache e Real-time

### Estrutura de Dados Aprimorada

```redis
# 🔐 SESSION MANAGEMENT AVANÇADO
session:{session_id} = {
  "user_id": "uuid",
  "company_id": "uuid", 
  "device_fingerprint": "hash",
  "ip_address": "192.168.1.100",
  "created_at": "2024-01-15T10:30:00Z",
  "last_activity": "2024-01-15T14:45:00Z",
  "activity_score": 95,
  "permissions": ["read:tenders", "write:quotes"],
  "auto_renew": true,
  "renewal_count": 3
}
TTL: 1800 # 30 minutos, renovado automaticamente

# 🚦 RATE LIMITING INTELIGENTE
rate_limit:{user_id}:{endpoint} = {
  "requests": 15,
  "window_start": "2024-01-15T14:00:00Z",
  "blocked": false,
  "warnings": 1
}
TTL: 3600 # 1 hora

rate_limit:company:{company_id}:global = {
  "requests": 450,
  "limit": 1000,
  "peak_time": "14:30"
}
TTL: 3600

# 🤖 AI CACHE SYSTEM (NOVO)
ai_cache:{prompt_hash} = {
  "response": "Análise detalhada do edital...",
  "confidence": 0.87,
  "tokens_used": 3850,
  "model": "llama3-8b",
  "created_at": "2024-01-15T14:30:00Z",
  "hit_count": 5,
  "validation_score": 0.92
}
TTL: 86400 # 24 horas para respostas de IA

ai_processing:{document_id} = {
  "status": "PROCESSING",
  "progress": 65,
  "current_step": "risk_assessment",
  "estimated_completion": "2024-01-15T14:35:00Z",
  "worker_id": "ai-worker-01"
}
TTL: 3600 # 1 hora

# 📊 PERFORMANCE CACHE (NOVO)
perf_cache:query:{query_hash} = {
  "result": {...},
  "execution_time_ms": 450,
  "cached_at": "2024-01-15T14:30:00Z",
  "hit_count": 12
}
TTL: 1800 # 30 minutos

perf_cache:aggregation:{agg_hash} = {
  "data": {...},
  "calculation_time_ms": 2300,
  "freshness": "2024-01-15T14:25:00Z"
}
TTL: 900 # 15 minutos para agregações

# 💬 REAL-TIME MESSAGING APRIMORADO
chat:{conversation_id}:messages = [
  {
    "id": "msg_uuid",
    "sender_id": "uuid",
    "content": "Análise do edital concluída!",
    "type": "SYSTEM", # TEXT, FILE, IMAGE, SYSTEM, AI_RESULT
    "timestamp": "2024-01-15T14:30:00Z",
    "metadata": {
      "ai_analysis_id": "uuid",
      "confidence": 0.87
    }
  }
]
TTL: 604800 # 7 dias

# 🟢 PRESENCE & ACTIVITY (NOVO)
presence:{user_id} = {
  "status": "online", # online, away, busy, offline
  "last_seen": "2024-01-15T14:30:00Z",
  "current_page": "/tenders/123/analysis",
  "device": "desktop",
  "activity": "viewing_ai_analysis"
}
TTL: 300 # 5 minutos

activity_feed:{company_id} = [
  {
    "user_id": "uuid",
    "action": "AI_ANALYSIS_COMPLETED",
    "entity": "tender_123",
    "timestamp": "2024-01-15T14:30:00Z",
    "metadata": {"risk_score": 75}
  }
]
TTL: 86400 # 24 horas

# 🔔 REAL-TIME NOTIFICATIONS (NOVO)
notifications:realtime:{user_id} = [
  {
    "id": "notif_uuid",
    "type": "AI_ANALYSIS_COMPLETE",
    "title": "Análise concluída",
    "data": {...},
    "created_at": "2024-01-15T14:30:00Z"
  }
]
TTL: 3600 # 1 hora

# 📈 SYSTEM METRICS (NOVO)
metrics:system = {
  "api_requests_per_minute": 145,
  "ai_jobs_queued": 3,
  "ai_jobs_processing": 2,
  "active_users": 28,
  "error_rate": 0.002,
  "avg_response_time_ms": 250
}
TTL: 60 # 1 minuto

# 🚨 ALERT SYSTEM (NOVO)
alerts:active = [
  {
    "id": "alert_uuid",
    "type": "HIGH_ERROR_RATE",
    "severity": "WARNING",
    "message": "Taxa de erro acima do normal (0.5%)",
    "created_at": "2024-01-15T14:25:00Z",
    "auto_resolve": true
  }
]
TTL: 3600 # 1 hora

# 🔄 ASYNC TASK MONITORING (NOVO)
task_status:{celery_task_id} = {
  "status": "PROCESSING",
  "progress": 45,
  "current_step": "text_extraction",
  "eta_seconds": 120,
  "worker": "celery-worker-02"
}
TTL: 3600 # 1 hora

# 🎯 BUSINESS INTELLIGENCE CACHE (NOVO)
bi_cache:dashboard:{company_id} = {
  "tender_stats": {
    "total_this_month": 12,
    "success_rate": 0.83,
    "avg_risk_score": 68
  },
  "ai_usage": {
    "documents_processed": 45,
    "total_cost": 125.50,
    "avg_confidence": 0.87
  },
  "generated_at": "2024-01-15T14:30:00Z"
}
TTL: 1800 # 30 minutos
```

### 8. 🔧 Configuração e Otimização Avançada

#### 📊 Estratégias de Indexação Avançada

```sql
-- Índices compostos para queries complexas
CREATE INDEX idx_tenders_ai_composite ON tenders (company_id, ai_processing_status, risk_score DESC, submission_deadline);
CREATE INDEX idx_documents_processing_composite ON documents (company_id, processing_status, created_at DESC);
CREATE INDEX idx_ai_jobs_queue_composite ON ai_processing_jobs (status, priority DESC, created_at);

-- Índices para análise temporal
CREATE INDEX idx_audit_logs_time_series ON audit_logs (company_id, created_at DESC, category);
CREATE INDEX idx_api_metrics_time_series ON api_metrics (date_only, endpoint, company_id);

-- Índices para full-text search
CREATE INDEX idx_tenders_fulltext ON tenders USING gin(to_tsvector('portuguese', title || ' ' || description));
CREATE INDEX idx_documents_fulltext ON documents USING gin(to_tsvector('portuguese', original_name));

-- Índices parciais para otimização
CREATE INDEX idx_sessions_active_only ON user_sessions (user_id, last_activity) WHERE is_active = true;
CREATE INDEX idx_security_events_unresolved ON security_events (created_at DESC) WHERE auto_resolved = false;
```

#### 🚀 Configurações de Performance

```sql
-- Configurações PostgreSQL otimizadas
-- postgresql.conf
shared_buffers = '256MB'
effective_cache_size = '1GB'
maintenance_work_mem = '64MB'
checkpoint_completion_target = 0.9
wal_buffers = '16MB'
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200

-- Configurações para AI workloads
work_mem = '32MB'  -- Para ordenações e agregações
max_connections = 200
shared_preload_libraries = 'pg_stat_statements'
```

#### 🔄 Particionamento de Tabelas

```sql
-- Particionamento da tabela audit_logs por mês
CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs 
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE audit_logs_2024_02 PARTITION OF audit_logs 
FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Particionamento da tabela api_metrics por semana
CREATE TABLE api_metrics_2024_w01 PARTITION OF api_metrics 
FOR VALUES FROM ('2024-01-01') TO ('2024-01-08');

-- Automatização de criação de partições
CREATE OR REPLACE FUNCTION create_monthly_partitions()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    table_name text;
BEGIN
    start_date := date_trunc('month', CURRENT_DATE + interval '1 month');
    end_date := start_date + interval '1 month';
    table_name := 'audit_logs_' || to_char(start_date, 'YYYY_MM');
    
    EXECUTE format('CREATE TABLE %I PARTITION OF audit_logs FOR VALUES FROM (%L) TO (%L)',
                   table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;
```

---

## 📦 Estratégias de Backup e Recuperação

### 🔄 Backup Automatizado

```yaml
# docker-compose.backup.yml
version: '3.8'
services:
  postgres-backup:
    image: prodrigestivill/postgres-backup-local
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_DB: tender_platform
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      BACKUP_KEEP_DAYS: 30
      BACKUP_KEEP_WEEKS: 8
      BACKUP_KEEP_MONTHS: 12
      HEALTHCHECK_PORT: 8080
    volumes:
      - ./backups/postgres:/backups
    depends_on:
      - postgres

  mongodb-backup:
    image: mongo:7
    command: >
      bash -c "
        while true; do
          mongodump --host mongodb:27017 --db tender_platform --out /backup/$(date +%Y%m%d_%H%M%S)
          find /backup -type d -mtime +30 -exec rm -rf {} +
          sleep 86400
        done
      "
    volumes:
      - ./backups/mongodb:/backup
    depends_on:
      - mongodb

  redis-backup:
    image: redis:7-alpine
    command: >
      sh -c "
        while true; do
          redis-cli -h redis --rdb /backup/dump_$(date +%Y%m%d_%H%M%S).rdb
          find /backup -name '*.rdb' -mtime +7 -delete
          sleep 21600
        done
      "
    volumes:
      - ./backups/redis:/backup
    depends_on:
      - redis
```

### 📋 Política de Retenção de Dados

```sql
-- Procedimento de limpeza automática
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Limpar logs de auditoria antigos (mantém 2 anos)
    DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '2 years';
    
    -- Limpar métricas de API antigas (mantém 6 meses)
    DELETE FROM api_metrics WHERE created_at < NOW() - INTERVAL '6 months';
    
    -- Limpar sessões expiradas
    DELETE FROM user_sessions WHERE expires_at < NOW() AND is_active = false;
    
    -- Limpar cache de IA antigo (mantém 30 dias)
    DELETE FROM ai_response_cache WHERE expires_at < NOW();
    
    -- Arquivar documentos antigos não utilizados
    UPDATE documents 
    SET is_archived = true, archived_at = NOW()
    WHERE last_accessed_at < NOW() - INTERVAL '1 year' 
    AND is_archived = false;
    
    -- Log da operação
    INSERT INTO audit_logs (action, entity_type, changes_summary, category)
    VALUES ('CLEANUP', 'SYSTEM', 'Limpeza automática de dados antigos executada', 'SYSTEM');
END;
$$ LANGUAGE plpgsql;

-- Agendar limpeza semanal
SELECT cron.schedule('cleanup-old-data', '0 2 * * 0', 'SELECT cleanup_old_data();');
```

---

## 🚀 Migração e Deploy

### 📝 Scripts de Migração

```python
# migrations/001_initial_schema.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Criar tabelas principais
    op.create_table('companies',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.VARCHAR(255), nullable=False),
        sa.Column('slug', sa.VARCHAR(100), nullable=False),
        # ... outros campos
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    
    # Criar índices iniciais
    op.create_index('idx_companies_slug', 'companies', ['slug'])
    
def downgrade():
    op.drop_table('companies')

# migrations/002_ai_system.py
def upgrade():
    # Adicionar tabelas do sistema de IA
    op.create_table('documents',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('company_id', postgresql.UUID(), nullable=False),
        # ... campos específicos de IA
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'])
    )
    
    op.create_table('ai_processing_jobs',
        # ... definição completa
    )
```

### 🏗️ Setup de Ambiente

```bash
#!/bin/bash
# scripts/setup_database.sh

echo "🚀 Configurando ambiente de banco de dados..."

# Criar diretórios necessários
mkdir -p backups/{postgres,mongodb,redis}
mkdir -p logs/{postgres,mongodb,redis}

# Configurar PostgreSQL
echo "📊 Configurando PostgreSQL..."
docker-compose exec postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
CREATE EXTENSION IF NOT EXISTS 'uuid-ossp';
CREATE EXTENSION IF NOT EXISTS 'pg_stat_statements';
CREATE EXTENSION IF NOT EXISTS 'pg_trgm';
"

# Aplicar migrações
echo "🔄 Aplicando migrações..."
alembic upgrade head

# Configurar MongoDB
echo "🍃 Configurando MongoDB..."
docker-compose exec mongodb mongo tender_platform --eval "
db.createUser({
  user: '${MONGODB_USER}',
  pwd: '${MONGODB_PASSWORD}',
  roles: ['readWrite']
});

// Criar índices iniciais
db.notifications.createIndex({ 'user_id': 1, 'created_at': -1 });
db.ai_processing_logs.createIndex({ 'document_id': 1, 'created_at': -1 });
"

# Configurar Redis
echo "🔴 Configurando Redis..."
docker-compose exec redis redis-cli CONFIG SET save "900 1 300 10 60 10000"

echo "✅ Setup completo!"
```

### 📋 Checklist de Deploy

```yaml
# deploy/checklist.yml
pre_deploy:
  - name: "Backup atual"
    command: "./scripts/backup_all.sh"
    required: true
  
  - name: "Verificar migrações"
    command: "alembic check"
    required: true
  
  - name: "Testes de integração"
    command: "pytest tests/integration/"
    required: true

deploy:
  - name: "Aplicar migrações"
    command: "alembic upgrade head"
    rollback: "alembic downgrade -1"
  
  - name: "Atualizar esquemas MongoDB"
    command: "./scripts/update_mongo_schema.sh"

post_deploy:
  - name: "Verificar saúde dos serviços"
    command: "./scripts/health_check.sh"
    timeout: 300
  
  - name: "Executar testes de fumaça"
    command: "pytest tests/smoke/"
    required: true
  
  - name: "Atualizar métricas"
    command: "./scripts/update_metrics.sh"
```

---

## 🎯 Métricas e Monitoramento

### 📊 KPIs de Performance

```sql
-- View para métricas de performance
CREATE VIEW performance_dashboard AS
SELECT 
    date_trunc('hour', created_at) as hour_bucket,
    COUNT(*) as total_requests,
    AVG(response_time_ms) as avg_response_time,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_response_time,
    COUNT(*) FILTER (WHERE status_code >= 400) as error_count,
    COUNT(*) FILTER (WHERE cache_hit = true) as cache_hits,
    AVG(ai_processing_time_ms) FILTER (WHERE ai_processing_time_ms > 0) as avg_ai_time
FROM api_metrics 
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY hour_bucket
ORDER BY hour_bucket DESC;

-- View para métricas de IA
CREATE VIEW ai_performance_dashboard AS
SELECT 
    date_trunc('day', created_at) as day_bucket,
    COUNT(*) as total_jobs,
    COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed_jobs,
    COUNT(*) FILTER (WHERE status = 'FAILED') as failed_jobs,
    AVG(processing_time_ms) as avg_processing_time,
    AVG(confidence_score) as avg_confidence,
    SUM(tokens_used) as total_tokens,
    SUM(cost_estimate) as total_cost
FROM ai_processing_jobs 
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY day_bucket
ORDER BY day_bucket DESC;
```

### 🚨 Alertas Automáticos

```sql
-- Função para detectar anomalias
CREATE OR REPLACE FUNCTION detect_anomalies()
RETURNS void AS $$
DECLARE
    error_rate DECIMAL;
    avg_response_time DECIMAL;
    ai_failure_rate DECIMAL;
BEGIN
    -- Calcular taxa de erro da última hora
    SELECT 
        COALESCE(COUNT(*) FILTER (WHERE status_code >= 400) * 100.0 / NULLIF(COUNT(*), 0), 0)
    INTO error_rate
    FROM api_metrics 
    WHERE created_at >= NOW() - INTERVAL '1 hour';
    
    -- Alerta para alta taxa de erro
    IF error_rate > 5.0 THEN
        INSERT INTO security_alerts (alert_type, severity, title, description)
        VALUES ('HIGH_ERROR_RATE', 'CRITICAL', 
                'Taxa de erro elevada', 
                format('Taxa de erro de %.2f%% na última hora', error_rate));
    END IF;
    
    -- Verificar performance de IA
    SELECT 
        COUNT(*) FILTER (WHERE status = 'FAILED') * 100.0 / NULLIF(COUNT(*), 0)
    INTO ai_failure_rate
    FROM ai_processing_jobs 
    WHERE created_at >= NOW() - INTERVAL '1 hour';
    
    IF ai_failure_rate > 10.0 THEN
        INSERT INTO security_alerts (alert_type, severity, title, description)
        VALUES ('AI_HIGH_FAILURE', 'HIGH', 
                'Alta taxa de falha na IA', 
                format('%.2f%% dos jobs de IA falharam na última hora', ai_failure_rate));
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Executar verificação a cada 5 minutos
SELECT cron.schedule('anomaly-detection', '*/5 * * * *', 'SELECT detect_anomalies();');
```

---

## 🧪 Testing e Validação

### 🔬 Testes de Performance

```python
# tests/performance/test_database_performance.py
import pytest
import asyncio
from sqlalchemy import text
from app.core.database import async_session

class TestDatabasePerformance:
    
    @pytest.mark.asyncio
    async def test_tender_search_performance(self):
        """Teste de performance para busca de licitações"""
        async with async_session() as session:
            start_time = time.time()
            
            result = await session.execute(text("""
                SELECT t.*, ta.risk_score, ta.confidence_score
                FROM tenders t
                LEFT JOIN tender_ai_analyses ta ON t.id = ta.tender_id
                WHERE t.company_id = :company_id
                AND t.submission_deadline > NOW()
                ORDER BY ta.risk_score DESC, t.created_at DESC
                LIMIT 50
            """), {"company_id": "test-company-id"})
            
            execution_time = time.time() - start_time
            
            # Performance deve ser menor que 100ms
            assert execution_time < 0.1, f"Query muito lenta: {execution_time}s"
    
    @pytest.mark.asyncio
    async def test_ai_cache_performance(self):
        """Teste de performance do cache de IA"""
        # Teste implementação de cache Redis
        pass

# tests/load/test_concurrent_ai_processing.py
class TestConcurrentAIProcessing:
    
    @pytest.mark.asyncio
    async def test_multiple_document_processing(self):
        """Teste de processamento concorrente de documentos"""
        tasks = []
        for i in range(10):
            task = asyncio.create_task(
                self.process_test_document(f"document_{i}.pdf")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verificar que todos processaram com sucesso
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) == 10
```

---

## 📋 Resumo das Melhorias Implementadas

### ✅ Novos Recursos Adicionados

1. **🤖 Sistema de IA Completo**
   - Tabelas para processamento de documentos
   - Jobs de IA com retry e monitoramento
   - Cache inteligente de respostas
   - Templates de prompts versionados

2. **🔐 Segurança Avançada**
   - Rate limiting inteligente
   - Sessões com controle temporal
   - Alertas de segurança automáticos
   - Auditoria detalhada

3. **📊 Monitoramento Robusto**
   - Métricas de performance em tempo real
   - Saúde dos serviços
   - Alertas automáticos
   - Dashboards de BI

4. **🔄 Processamento Assíncrono**
   - Gestão completa de tarefas Celery
   - Monitoramento de workers
   - Filas de processamento otimizadas

5. **📁 Gestão de Arquivos**
   - Sistema completo de upload
   - Versionamento de arquivos
   - Logs de acesso detalhados

6. **🚀 Performance e Escalabilidade**
   - Índices otimizados
   - Particionamento de tabelas
   - Cache inteligente multinível
   - Limpeza automática de dados

### 📈 Benefícios da Arquitetura Aprimorada

- **Escalabilidade**: Suporta crescimento exponencial de dados e usuários
- **Performance**: Otimizações avançadas para sub-segundo de resposta
- **Confiabilidade**: Sistema robusto com retry, fallbacks e monitoramento
- **Segurança**: Proteção avançada contra ataques e uso indevido
- **Observabilidade**: Visibilidade completa de todas as operações
- **Manutenibilidade**: Estrutura organizada e bem documentada

A arquitetura está agora alinhada com as melhores práticas de sistemas distribuídos modernos e preparada para suportar o crescimento da plataforma de licitações com integração de IA de forma robusta e escalável.

// Histórico de atividades detalhado
activity_history: {
  _id: ObjectId,
  user_id: "uuid",
  company_id: "uuid",
  session_id: "uuid",
  
  // Atividade realizada
  activity_type: "TENDER_UPLOADED",
  description: "Usuário fez upload do edital #2024-001",
  
  // Contexto detalhado
  context: {
    entity_type: "TENDER",
    entity_id: "uuid",
    entity_name: "Licitação Equipamentos TI",
    action: "CREATE",
    details: {
      file_name: "edital_001.pdf",
      file_size: 2048576,
      processing_time: 45.2
    }
  },
  
  // Informações técnicas
  technical_info: {
    ip_address: "192.168.1.100",
    user_agent: "Mozilla/5.0...",
    platform: "web",
    feature_used: "file_upload"
  },
  
  // Tags para busca
  tags: ["upload", "tender", "pdf"],
  
  timestamp: ISODate()
}

// Configurações dinâmicas personalizáveis
dynamic_settings: {
  _id: ObjectId,
  company_id: "uuid",
  user_id: "uuid", // NULL para configurações da empresa
  
  // Tipo de configuração
  setting_type: "KANBAN_LAYOUT", // KANBAN_LAYOUT, DASHBOARD_WIDGETS, FORM_TEMPLATE
  setting_name: "projeto_alpha_board",
  
  // Configuração flexível
  configuration: {
    layout: "columns",
    columns: [
      {
        id: "todo",
        name: "A Fazer",
        color: "#e74c3c",
        position: 0,
        limit: 10
      },
      {
        id: "progress",
        name: "Em Progresso", 
        color: "#f39c12",
        position: 1,
        limit: 5
      },
      {
        id: "done",
        name: "Concluído",
        color: "#27ae60",
        position: 2,
        limit: null
      }
    ],
    automations: [
      {
        trigger: "card_moved_to_done",
        action: "send_notification",
        target: "card_assignee"
      }
    ]
  },
  
  // Versioning
  version: 1,
  is_active: true,
  
  created_at: ISODate(),
  updated_at: ISODate()
}

// Templates dinâmicos
dynamic_templates: {
  _id: ObjectId,
  company_id: "uuid",
  
  template_type: "EMAIL_QUOTE", // EMAIL_QUOTE, PDF_REPORT, FORM_LAYOUT
  name: "Template Cotação Padrão",
  description: "Template para envio de cotações por email",
  
  // Template flexível
  template: {
    subject: "Solicitação de Cotação - {{tender.number}}",
    body: `
      Prezado {{supplier.name}},
      
      Solicito cotação para os itens em anexo...
      
      Prazo: {{tender.deadline}}
    `,
    styles: {
      color_primary: "#3498db",
      font_family: "Arial, sans-serif"
    },
    variables: ["tender", "supplier", "items", "company"]
  },
  