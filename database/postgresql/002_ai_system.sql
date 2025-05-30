-- ============================================================================
-- 🤖 SISTEMA DE IA E PROCESSAMENTO DE DOCUMENTOS
-- ============================================================================

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
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
    completed_at TIMESTAMP WITH TIME ZONE
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
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 📁 SISTEMA DE ARQUIVOS E STORAGE
-- ============================================================================

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
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 🔄 SISTEMA DE TAREFAS ASSÍNCRONAS (CELERY)
-- ============================================================================

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
    completed_at TIMESTAMP WITH TIME ZONE
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
    
    CONSTRAINT celery_workers_hostname_name_unique UNIQUE (hostname, worker_name)
);
