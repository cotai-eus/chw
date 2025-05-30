-- ============================================================================
-- 🔧 TRIGGERS E FUNÇÕES AVANÇADAS
-- ============================================================================

-- ============================================================================
-- 🕒 TRIGGERS PARA UPDATED_AT
-- ============================================================================

-- Aplicar trigger updated_at nas tabelas principais
CREATE TRIGGER trigger_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_user_sessions_updated_at
    BEFORE UPDATE ON user_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_rate_limit_tracking_updated_at
    BEFORE UPDATE ON rate_limit_tracking
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_rate_limit_policies_updated_at
    BEFORE UPDATE ON rate_limit_policies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_ai_prompt_templates_updated_at
    BEFORE UPDATE ON ai_prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_files_updated_at
    BEFORE UPDATE ON files
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_celery_workers_updated_at
    BEFORE UPDATE ON celery_workers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_kanban_boards_updated_at
    BEFORE UPDATE ON kanban_boards
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_kanban_lists_updated_at
    BEFORE UPDATE ON kanban_lists
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_kanban_cards_updated_at
    BEFORE UPDATE ON kanban_cards
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_suppliers_updated_at
    BEFORE UPDATE ON suppliers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_tenders_updated_at
    BEFORE UPDATE ON tenders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_quotes_updated_at
    BEFORE UPDATE ON quotes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 🚨 TRIGGERS DE AUDITORIA
-- ============================================================================

-- Triggers de auditoria para tabelas críticas
CREATE TRIGGER trigger_users_audit
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER trigger_companies_audit
    AFTER INSERT OR UPDATE OR DELETE ON companies
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER trigger_tenders_audit
    AFTER INSERT OR UPDATE OR DELETE ON tenders
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER trigger_documents_audit
    AFTER INSERT OR UPDATE OR DELETE ON documents
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER trigger_kanban_cards_audit
    AFTER INSERT OR UPDATE OR DELETE ON kanban_cards
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- ============================================================================
-- 🔐 FUNÇÕES DE SEGURANÇA
-- ============================================================================

-- Função para validar força da senha
CREATE OR REPLACE FUNCTION validate_password_strength(password TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- Mínimo 8 caracteres
    IF LENGTH(password) < 8 THEN
        RETURN FALSE;
    END IF;
    
    -- Deve conter ao menos uma letra maiúscula
    IF password !~ '[A-Z]' THEN
        RETURN FALSE;
    END IF;
    
    -- Deve conter ao menos uma letra minúscula
    IF password !~ '[a-z]' THEN
        RETURN FALSE;
    END IF;
    
    -- Deve conter ao menos um número
    IF password !~ '[0-9]' THEN
        RETURN FALSE;
    END IF;
    
    -- Deve conter ao menos um caractere especial
    IF password !~ '[!@#$%^&*(),.?":{}|<>]' THEN
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Função para detectar tentativas de login suspeitas
CREATE OR REPLACE FUNCTION detect_suspicious_login(
    p_user_id UUID,
    p_ip_address INET,
    p_user_agent TEXT,
    p_success BOOLEAN
)
RETURNS VOID AS $$
DECLARE
    failed_attempts INTEGER;
    location_changes INTEGER;
    user_agent_changes INTEGER;
BEGIN
    -- Contar tentativas falhadas nas últimas 15 minutos
    SELECT COUNT(*)
    INTO failed_attempts
    FROM audit_logs
    WHERE user_id = p_user_id
    AND action = 'LOGIN_FAILED'
    AND created_at >= NOW() - INTERVAL '15 minutes';
    
    -- Verificar mudanças de localização suspeitas
    SELECT COUNT(DISTINCT ip_address)
    INTO location_changes
    FROM audit_logs
    WHERE user_id = p_user_id
    AND created_at >= NOW() - INTERVAL '1 hour'
    AND ip_address IS NOT NULL;
    
    -- Verificar mudanças de user agent
    SELECT COUNT(DISTINCT user_agent)
    INTO user_agent_changes
    FROM audit_logs
    WHERE user_id = p_user_id
    AND created_at >= NOW() - INTERVAL '1 hour'
    AND user_agent IS NOT NULL;
    
    -- Gerar alertas baseado nos critérios
    IF failed_attempts >= 5 THEN
        INSERT INTO security_alerts (
            alert_type, severity, title, description,
            user_id, source_ip, event_data
        ) VALUES (
            'BRUTE_FORCE', 'HIGH',
            'Múltiplas tentativas de login falhadas',
            format('Usuário %s teve %s tentativas de login falhadas em 15 minutos', p_user_id, failed_attempts),
            p_user_id, p_ip_address,
            jsonb_build_object('failed_attempts', failed_attempts, 'time_window', '15 minutes')
        );
    END IF;
    
    IF location_changes >= 3 THEN
        INSERT INTO security_alerts (
            alert_type, severity, title, description,
            user_id, source_ip, event_data
        ) VALUES (
            'ANOMALY', 'MEDIUM',
            'Múltiplas localizações de acesso',
            format('Usuário %s acessou de %s localizações diferentes em 1 hora', p_user_id, location_changes),
            p_user_id, p_ip_address,
            jsonb_build_object('location_changes', location_changes, 'time_window', '1 hour')
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 📊 FUNÇÕES DE MÉTRICAS E ANALYTICS
-- ============================================================================

-- Função para calcular score de atividade de usuário
CREATE OR REPLACE FUNCTION calculate_user_activity_score(p_user_id UUID)
RETURNS INTEGER AS $$
DECLARE
    login_score INTEGER := 0;
    action_score INTEGER := 0;
    session_score INTEGER := 0;
    total_score INTEGER := 0;
BEGIN
    -- Score baseado em logins (últimos 30 dias)
    SELECT CASE 
        WHEN COUNT(*) >= 20 THEN 30
        WHEN COUNT(*) >= 10 THEN 20
        WHEN COUNT(*) >= 5 THEN 15
        WHEN COUNT(*) >= 1 THEN 10
        ELSE 0
    END INTO login_score
    FROM audit_logs
    WHERE user_id = p_user_id
    AND action = 'LOGIN_SUCCESS'
    AND created_at >= NOW() - INTERVAL '30 days';
    
    -- Score baseado em ações (últimos 30 dias)
    SELECT CASE 
        WHEN COUNT(*) >= 100 THEN 40
        WHEN COUNT(*) >= 50 THEN 30
        WHEN COUNT(*) >= 20 THEN 20
        WHEN COUNT(*) >= 5 THEN 10
        ELSE 0
    END INTO action_score
    FROM audit_logs
    WHERE user_id = p_user_id
    AND action IN ('CREATE', 'UPDATE', 'DELETE')
    AND created_at >= NOW() - INTERVAL '30 days';
    
    -- Score baseado em tempo de sessão (últimos 30 dias)
    SELECT CASE 
        WHEN AVG(EXTRACT(epoch FROM (last_activity - created_at))/3600) >= 4 THEN 30
        WHEN AVG(EXTRACT(epoch FROM (last_activity - created_at))/3600) >= 2 THEN 20
        WHEN AVG(EXTRACT(epoch FROM (last_activity - created_at))/3600) >= 1 THEN 15
        WHEN AVG(EXTRACT(epoch FROM (last_activity - created_at))/3600) >= 0.5 THEN 10
        ELSE 0
    END INTO session_score
    FROM user_sessions
    WHERE user_id = p_user_id
    AND created_at >= NOW() - INTERVAL '30 days';
    
    total_score := login_score + action_score + session_score;
    
    -- Garantir que o score está entre 0 e 100
    RETURN LEAST(100, total_score);
END;
$$ LANGUAGE plpgsql;

-- Função para calcular métricas de licitação
CREATE OR REPLACE FUNCTION calculate_tender_metrics(p_company_id UUID)
RETURNS TABLE(
    total_tenders INTEGER,
    success_rate DECIMAL(5,2),
    avg_risk_score DECIMAL(5,2),
    avg_opportunity_score DECIMAL(5,2),
    ai_analysis_coverage DECIMAL(5,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_tenders,
        (COUNT(*) FILTER (WHERE status = 'WON') * 100.0 / NULLIF(COUNT(*), 0))::DECIMAL(5,2) as success_rate,
        AVG(risk_score)::DECIMAL(5,2) as avg_risk_score,
        AVG(opportunity_score)::DECIMAL(5,2) as avg_opportunity_score,
        (COUNT(*) FILTER (WHERE ai_processing_status = 'COMPLETED') * 100.0 / NULLIF(COUNT(*), 0))::DECIMAL(5,2) as ai_analysis_coverage
    FROM tenders
    WHERE company_id = p_company_id
    AND created_at >= NOW() - INTERVAL '1 year';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 🤖 FUNÇÕES PARA SISTEMA DE IA
-- ============================================================================

-- Função para processar documento com IA
CREATE OR REPLACE FUNCTION process_document_with_ai(
    p_document_id UUID,
    p_job_type VARCHAR(50),
    p_ai_model VARCHAR(100),
    p_priority INTEGER DEFAULT 5
)
RETURNS UUID AS $$
DECLARE
    job_id UUID;
    celery_task_id VARCHAR(255);
BEGIN
    -- Gerar ID único para o task Celery
    celery_task_id := 'ai_process_' || gen_random_uuid()::TEXT;
    
    -- Criar job de processamento
    INSERT INTO ai_processing_jobs (
        document_id,
        job_type,
        ai_model,
        priority,
        celery_task_id,
        status
    ) VALUES (
        p_document_id,
        p_job_type,
        p_ai_model,
        p_priority,
        celery_task_id,
        'QUEUED'
    ) RETURNING id INTO job_id;
    
    -- Atualizar status do documento
    UPDATE documents 
    SET processing_status = 'PROCESSING',
        processing_started_at = NOW()
    WHERE id = p_document_id;
    
    -- Log da ação
    INSERT INTO audit_logs (
        action, entity_type, entity_id,
        category, subcategory,
        changes_summary
    ) VALUES (
        'AI_PROCESS_STARTED', 'AI_JOB', job_id,
        'AI_OPERATION', 'DOCUMENT_PROCESSING',
        format('Iniciado processamento de IA para documento %s com modelo %s', p_document_id, p_ai_model)
    );
    
    RETURN job_id;
END;
$$ LANGUAGE plpgsql;

-- Função para atualizar cache de IA
CREATE OR REPLACE FUNCTION update_ai_cache(
    p_prompt_hash VARCHAR(128),
    p_parameters_hash VARCHAR(128),
    p_response_content TEXT,
    p_confidence_score DECIMAL(5,4),
    p_tokens_used INTEGER,
    p_processing_time_ms BIGINT
)
RETURNS VOID AS $$
DECLARE
    cache_key VARCHAR(128);
    expires_at TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Gerar chave do cache
    cache_key := MD5(p_prompt_hash || p_parameters_hash);
    
    -- Definir expiração baseada na confiança
    IF p_confidence_score >= 0.9 THEN
        expires_at := NOW() + INTERVAL '7 days';
    ELSIF p_confidence_score >= 0.8 THEN
        expires_at := NOW() + INTERVAL '3 days';
    ELSIF p_confidence_score >= 0.7 THEN
        expires_at := NOW() + INTERVAL '1 day';
    ELSE
        expires_at := NOW() + INTERVAL '6 hours';
    END IF;
    
    -- Inserir ou atualizar cache
    INSERT INTO ai_response_cache (
        cache_key,
        prompt_hash,
        parameters_hash,
        response_content,
        confidence_score,
        tokens_used,
        processing_time_ms,
        expires_at
    ) VALUES (
        cache_key,
        p_prompt_hash,
        p_parameters_hash,
        p_response_content,
        p_confidence_score,
        p_tokens_used,
        p_processing_time_ms,
        expires_at
    )
    ON CONFLICT (cache_key) DO UPDATE SET
        response_content = EXCLUDED.response_content,
        confidence_score = EXCLUDED.confidence_score,
        tokens_used = EXCLUDED.tokens_used,
        processing_time_ms = EXCLUDED.processing_time_ms,
        hit_count = ai_response_cache.hit_count + 1,
        last_hit_at = NOW(),
        expires_at = EXCLUDED.expires_at;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 🔄 FUNÇÕES DE LIMPEZA E MANUTENÇÃO
-- ============================================================================

-- Função para limpeza automática de dados antigos
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS VOID AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Limpar logs de auditoria antigos (mantém 2 anos)
    DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '2 years';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Removidos % registros de audit_logs', deleted_count;
    
    -- Limpar métricas de API antigas (mantém 6 meses)
    DELETE FROM api_metrics WHERE created_at < NOW() - INTERVAL '6 months';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Removidos % registros de api_metrics', deleted_count;
    
    -- Limpar atividades de sessão antigas (mantém 3 meses)
    DELETE FROM session_activities WHERE created_at < NOW() - INTERVAL '3 months';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Removidos % registros de session_activities', deleted_count;
    
    -- Limpar sessões expiradas e inativas
    DELETE FROM user_sessions 
    WHERE (expires_at < NOW() OR last_activity < NOW() - INTERVAL '30 days') 
    AND is_active = false;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Removidas % sessões expiradas', deleted_count;
    
    -- Limpar cache de IA expirado
    DELETE FROM ai_response_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Removidos % registros de cache de IA', deleted_count;
    
    -- Limpar logs de acesso a arquivos antigos (mantém 1 ano)
    DELETE FROM file_access_logs WHERE created_at < NOW() - INTERVAL '1 year';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Removidos % logs de acesso a arquivos', deleted_count;
    
    -- Arquivar documentos antigos não utilizados
    UPDATE documents 
    SET is_archived = true, archived_at = NOW()
    WHERE last_accessed_at < NOW() - INTERVAL '1 year' 
    AND is_archived = false
    AND processing_status = 'COMPLETED';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Arquivados % documentos antigos', deleted_count;
    
    -- Log da operação
    INSERT INTO audit_logs (
        action, entity_type, changes_summary, 
        category, subcategory, severity
    ) VALUES (
        'CLEANUP', 'SYSTEM', 'Limpeza automática de dados antigos executada',
        'SYSTEM', 'MAINTENANCE', 'INFO'
    );
END;
$$ LANGUAGE plpgsql;

-- Função para otimização de índices
CREATE OR REPLACE FUNCTION optimize_database()
RETURNS VOID AS $$
DECLARE
    table_name TEXT;
BEGIN
    -- Reindexar tabelas principais
    FOR table_name IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename IN ('audit_logs', 'api_metrics', 'user_sessions', 'documents', 'tenders')
    LOOP
        EXECUTE format('REINDEX TABLE %I', table_name);
        RAISE NOTICE 'Reindexada tabela %', table_name;
    END LOOP;
    
    -- Atualizar estatísticas
    ANALYZE;
    
    -- Log da operação
    INSERT INTO audit_logs (
        action, entity_type, changes_summary,
        category, subcategory, severity
    ) VALUES (
        'OPTIMIZE', 'SYSTEM', 'Otimização de banco de dados executada',
        'SYSTEM', 'MAINTENANCE', 'INFO'
    );
    
    RAISE NOTICE 'Otimização do banco de dados concluída';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- ⚡ FUNÇÕES DE PERFORMANCE
-- ============================================================================

-- Função para detectar queries lentas
CREATE OR REPLACE FUNCTION detect_slow_queries()
RETURNS TABLE(
    query TEXT,
    calls INTEGER,
    total_time NUMERIC,
    mean_time NUMERIC,
    max_time NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pss.query,
        pss.calls::INTEGER,
        pss.total_exec_time::NUMERIC,
        pss.mean_exec_time::NUMERIC,
        pss.max_exec_time::NUMERIC
    FROM pg_stat_statements pss
    WHERE pss.mean_exec_time > 1000 -- Queries com mais de 1 segundo de média
    ORDER BY pss.mean_exec_time DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;

-- Função para monitorar uso de índices
CREATE OR REPLACE FUNCTION monitor_index_usage()
RETURNS TABLE(
    schemaname TEXT,
    tablename TEXT,
    indexname TEXT,
    idx_tup_read BIGINT,
    idx_tup_fetch BIGINT,
    usage_ratio NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        psi.schemaname::TEXT,
        psi.relname::TEXT as tablename,
        psi.indexrelname::TEXT as indexname,
        psi.idx_tup_read,
        psi.idx_tup_fetch,
        CASE 
            WHEN psi.idx_tup_read = 0 THEN 0
            ELSE ROUND((psi.idx_tup_fetch::NUMERIC / psi.idx_tup_read) * 100, 2)
        END as usage_ratio
    FROM pg_stat_user_indexes psi
    JOIN pg_index pi ON psi.indexrelid = pi.indexrelid
    WHERE psi.schemaname = 'public'
    ORDER BY psi.idx_tup_read DESC;
END;
$$ LANGUAGE plpgsql;
