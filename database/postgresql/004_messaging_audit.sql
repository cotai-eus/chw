-- ============================================================================
-- 💬 SISTEMA DE MENSAGENS E COMUNICAÇÃO
-- ============================================================================

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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 🚨 LOGS DE AUDITORIA APRIMORADOS
-- ============================================================================

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
    date_only DATE GENERATED ALWAYS AS (created_at::DATE) STORED
);

-- Alertas e notificações de segurança
CREATE TABLE security_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Classificação do alerta
    alert_type VARCHAR(50) NOT NULL, -- BRUTE_FORCE, ANOMALY, BREACH_ATTEMPT
    severity VARCHAR(20) NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    priority INTEGER DEFAULT 5, -- 1-10
    
    -- Contexto
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT,
    
    -- Entidades afetadas
    user_id UUID REFERENCES users(id),
    company_id UUID REFERENCES companies(id),
    affected_entities JSONB DEFAULT '[]',
    
    -- Dados técnicos
    source_ip INET,
    event_data JSONB DEFAULT '{}',
    correlation_id VARCHAR(255),
    
    -- Status e resolução
    status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, INVESTIGATING, RESOLVED, FALSE_POSITIVE
    auto_resolved BOOLEAN DEFAULT FALSE,
    resolution_time_minutes INTEGER,
    
    -- Ações tomadas
    actions_taken JSONB DEFAULT '[]',
    assigned_to UUID REFERENCES users(id),
    
    -- Timestamps
    first_occurrence TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_occurrence TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- 📊 SISTEMA DE RELATÓRIOS E ANALYTICS
-- ============================================================================

-- Relatórios salvos
CREATE TABLE saved_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id),
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    report_type VARCHAR(50) NOT NULL, -- TENDER_PERFORMANCE, USER_ACTIVITY, AI_USAGE
    
    -- Configuração do relatório
    filters JSONB DEFAULT '{}',
    grouping JSONB DEFAULT '{}',
    sorting JSONB DEFAULT '{}',
    
    -- Metadados
    data_sources TEXT[], -- Tabelas/endpoints utilizados
    refresh_interval_minutes INTEGER, -- NULL = manual
    last_generated_at TIMESTAMP WITH TIME ZONE,
    
    -- Compartilhamento
    is_public BOOLEAN DEFAULT FALSE,
    shared_with_users UUID[] DEFAULT '{}',
    shared_with_roles TEXT[] DEFAULT '{}',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    generation_status VARCHAR(20) DEFAULT 'READY', -- READY, GENERATING, ERROR
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Execuções de relatórios
CREATE TABLE report_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES saved_reports(id) ON DELETE CASCADE,
    executed_by UUID REFERENCES users(id),
    
    -- Parâmetros da execução
    parameters JSONB DEFAULT '{}',
    date_range JSONB DEFAULT '{}',
    
    -- Resultado
    status VARCHAR(20) DEFAULT 'RUNNING', -- RUNNING, COMPLETED, FAILED
    result_data JSONB,
    error_message TEXT,
    
    -- Métricas
    execution_time_ms INTEGER,
    rows_processed INTEGER DEFAULT 0,
    file_size_bytes BIGINT,
    
    -- Output
    output_format VARCHAR(20) DEFAULT 'JSON', -- JSON, CSV, PDF, EXCEL
    file_path VARCHAR(500),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- 🔧 FUNÇÕES E TRIGGERS DE AUDITORIA
-- ============================================================================

-- Função genérica para auditoria
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    old_data JSONB;
    new_data JSONB;
    action_type VARCHAR(10);
BEGIN
    -- Determinar tipo de ação
    IF TG_OP = 'DELETE' THEN
        old_data = to_jsonb(OLD);
        new_data = NULL;
        action_type = 'DELETE';
    ELSIF TG_OP = 'UPDATE' THEN
        old_data = to_jsonb(OLD);
        new_data = to_jsonb(NEW);
        action_type = 'UPDATE';
    ELSIF TG_OP = 'INSERT' THEN
        old_data = NULL;
        new_data = to_jsonb(NEW);
        action_type = 'CREATE';
    END IF;
    
    -- Inserir log de auditoria
    INSERT INTO audit_logs (
        action,
        entity_type,
        entity_id,
        old_values,
        new_values,
        category,
        severity,
        created_at
    ) VALUES (
        action_type,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        old_data,
        new_data,
        'DATA',
        'INFO',
        NOW()
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Função para atualizar timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 📈 VIEWS DE PERFORMANCE E ANALYTICS
-- ============================================================================

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
    AVG(CASE WHEN status = 'COMPLETED' THEN 
        (SELECT confidence_score FROM tender_ai_analyses 
         WHERE ai_job_id = ai_processing_jobs.id LIMIT 1) 
    END) as avg_confidence,
    SUM(tokens_used) as total_tokens,
    SUM(cost_estimate) as total_cost
FROM ai_processing_jobs 
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY day_bucket
ORDER BY day_bucket DESC;

-- View para dashboard de licitações
CREATE VIEW tender_dashboard AS
SELECT 
    t.company_id,
    COUNT(*) as total_tenders,
    COUNT(*) FILTER (WHERE t.status = 'WON') as won_tenders,
    COUNT(*) FILTER (WHERE t.status = 'LOST') as lost_tenders,
    COUNT(*) FILTER (WHERE t.ai_processing_status = 'COMPLETED') as ai_analyzed,
    AVG(t.risk_score) FILTER (WHERE t.risk_score > 0) as avg_risk_score,
    AVG(t.opportunity_score) FILTER (WHERE t.opportunity_score > 0) as avg_opportunity_score,
    COUNT(*) FILTER (WHERE t.submission_deadline > NOW()) as active_tenders
FROM tenders t
WHERE t.created_at >= NOW() - INTERVAL '1 year'
GROUP BY t.company_id;

-- View para análise de usuários ativos
CREATE VIEW user_activity_summary AS
SELECT 
    u.company_id,
    u.id as user_id,
    u.first_name || ' ' || u.last_name as full_name,
    u.role,
    u.last_login_at,
    s.total_sessions,
    s.avg_session_duration,
    a.total_actions,
    a.last_action_at
FROM users u
LEFT JOIN (
    SELECT 
        user_id,
        COUNT(*) as total_sessions,
        AVG(EXTRACT(epoch FROM (COALESCE(last_activity, NOW()) - created_at))/60) as avg_session_duration
    FROM user_sessions 
    WHERE created_at >= NOW() - INTERVAL '30 days'
    GROUP BY user_id
) s ON u.id = s.user_id
LEFT JOIN (
    SELECT 
        user_id,
        COUNT(*) as total_actions,
        MAX(created_at) as last_action_at
    FROM audit_logs 
    WHERE created_at >= NOW() - INTERVAL '30 days'
    GROUP BY user_id
) a ON u.id = a.user_id
WHERE u.status = 'ACTIVE';
