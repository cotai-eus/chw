-- ============================================================================
-- 🗄️ Schema Principal PostgreSQL - Arquitetura Modular e Escalável
-- ============================================================================

-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- 1. 🏢 SISTEMA DE EMPRESAS E USUÁRIOS
-- ============================================================================

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

-- ============================================================================
-- 2. 🔐 SISTEMA DE SESSÕES E SEGURANÇA
-- ============================================================================

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
    last_renewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 3. 🚨 SISTEMA DE RATE LIMITING E SEGURANÇA
-- ============================================================================

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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 4. 📊 SISTEMA DE MONITORAMENTO E MÉTRICAS
-- ============================================================================

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
    hour_bucket TIMESTAMP GENERATED ALWAYS AS (date_trunc('hour', created_at)) STORED
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
    minute_bucket TIMESTAMP GENERATED ALWAYS AS (date_trunc('minute', created_at)) STORED
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
    
    CONSTRAINT service_health_hostname_service_unique UNIQUE (hostname, service_name)
);
