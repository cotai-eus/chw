-- ============================================================================
-- 🚀 ÍNDICES E OTIMIZAÇÕES DE PERFORMANCE
-- ============================================================================

-- ============================================================================
-- 📊 ÍNDICES BÁSICOS
-- ============================================================================

-- Índices para tabela companies
CREATE INDEX idx_companies_slug ON companies(slug);
CREATE INDEX idx_companies_status ON companies(status);
CREATE INDEX idx_companies_created ON companies(created_at DESC);

-- Índices para tabela users
CREATE INDEX idx_users_company ON users(company_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_last_login ON users(last_login_at DESC);

-- Índices para user_sessions
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(token_hash);
CREATE INDEX idx_user_sessions_active ON user_sessions(is_active, expires_at);
CREATE INDEX idx_user_sessions_activity ON user_sessions(last_activity DESC);
CREATE INDEX idx_user_sessions_device ON user_sessions(device_fingerprint);

-- Índices para session_activities
CREATE INDEX idx_session_activities_session ON session_activities(session_id);
CREATE INDEX idx_session_activities_created ON session_activities(created_at DESC);
CREATE INDEX idx_session_activities_type ON session_activities(activity_type);

-- ============================================================================
-- 🔐 ÍNDICES PARA SEGURANÇA E RATE LIMITING
-- ============================================================================

-- Índices para rate_limit_tracking
CREATE INDEX idx_rate_limit_user ON rate_limit_tracking(user_id);
CREATE INDEX idx_rate_limit_company ON rate_limit_tracking(company_id);
CREATE INDEX idx_rate_limit_ip ON rate_limit_tracking(ip_address);
CREATE INDEX idx_rate_limit_window ON rate_limit_tracking(window_start, endpoint_pattern);
CREATE INDEX idx_rate_limit_blocked ON rate_limit_tracking(is_blocked, blocked_until);

-- Índices para security_events
CREATE INDEX idx_security_events_user ON security_events(user_id);
CREATE INDEX idx_security_events_company ON security_events(company_id);
CREATE INDEX idx_security_events_type ON security_events(event_type);
CREATE INDEX idx_security_events_severity ON security_events(severity);
CREATE INDEX idx_security_events_created ON security_events(created_at DESC);

-- Índices para rate_limit_policies
CREATE INDEX idx_rate_policies_company ON rate_limit_policies(company_id);
CREATE INDEX idx_rate_policies_endpoint ON rate_limit_policies(endpoint_pattern);
CREATE INDEX idx_rate_policies_active ON rate_limit_policies(is_active);

-- ============================================================================
-- 📊 ÍNDICES PARA MÉTRICAS E MONITORAMENTO
-- ============================================================================

-- Índices para api_metrics
CREATE INDEX idx_api_metrics_endpoint ON api_metrics(endpoint);
CREATE INDEX idx_api_metrics_user ON api_metrics(user_id);
CREATE INDEX idx_api_metrics_company ON api_metrics(company_id);
CREATE INDEX idx_api_metrics_date ON api_metrics(date_only);
CREATE INDEX idx_api_metrics_hour ON api_metrics(hour_bucket);
CREATE INDEX idx_api_metrics_performance ON api_metrics(response_time_ms DESC);
CREATE INDEX idx_api_metrics_status ON api_metrics(status_code);

-- Índices para system_metrics
CREATE INDEX idx_system_metrics_type ON system_metrics(metric_type);
CREATE INDEX idx_system_metrics_service ON system_metrics(service_name);
CREATE INDEX idx_system_metrics_date ON system_metrics(date_only);
CREATE INDEX idx_system_metrics_minute ON system_metrics(minute_bucket);
CREATE INDEX idx_system_metrics_alert ON system_metrics(alert_triggered, created_at DESC);

-- Índices para service_health
CREATE INDEX idx_service_health_service ON service_health(service_name);
CREATE INDEX idx_service_health_status ON service_health(status);
CREATE INDEX idx_service_health_check ON service_health(last_check DESC);

-- ============================================================================
-- 🤖 ÍNDICES PARA SISTEMA DE IA
-- ============================================================================

-- Índices para documents
CREATE INDEX idx_documents_company ON documents(company_id);
CREATE INDEX idx_documents_user ON documents(uploaded_by);
CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_documents_hash ON documents(file_hash);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_created ON documents(created_at DESC);

-- Índices para ai_processing_jobs
CREATE INDEX idx_ai_jobs_document ON ai_processing_jobs(document_id);
CREATE INDEX idx_ai_jobs_status ON ai_processing_jobs(status);
CREATE INDEX idx_ai_jobs_created ON ai_processing_jobs(created_at DESC);
CREATE INDEX idx_ai_jobs_celery ON ai_processing_jobs(celery_task_id);
CREATE INDEX idx_ai_jobs_priority ON ai_processing_jobs(priority DESC, created_at);

-- Índices para text_extractions
CREATE INDEX idx_text_extractions_document ON text_extractions(document_id);
CREATE INDEX idx_text_extractions_job ON text_extractions(ai_job_id);

-- Índices para ai_prompt_templates
CREATE INDEX idx_ai_prompts_category ON ai_prompt_templates(category);
CREATE INDEX idx_ai_prompts_use_case ON ai_prompt_templates(use_case);
CREATE INDEX idx_ai_prompts_active ON ai_prompt_templates(is_active);

-- Índices para ai_response_cache
CREATE INDEX idx_ai_cache_key ON ai_response_cache(cache_key);
CREATE INDEX idx_ai_cache_prompt ON ai_response_cache(prompt_hash);
CREATE INDEX idx_ai_cache_expires ON ai_response_cache(expires_at);
CREATE INDEX idx_ai_cache_hits ON ai_response_cache(hit_count DESC);

-- ============================================================================
-- 📁 ÍNDICES PARA ARQUIVOS
-- ============================================================================

-- Índices para files
CREATE INDEX idx_files_company ON files(company_id);
CREATE INDEX idx_files_user ON files(uploaded_by);
CREATE INDEX idx_files_hash ON files(file_hash);
CREATE INDEX idx_files_category ON files(category);
CREATE INDEX idx_files_processing ON files(processing_status);
CREATE INDEX idx_files_created ON files(created_at DESC);

-- Índices para file_access_logs
CREATE INDEX idx_file_access_file ON file_access_logs(file_id);
CREATE INDEX idx_file_access_user ON file_access_logs(user_id);
CREATE INDEX idx_file_access_created ON file_access_logs(created_at DESC);

-- ============================================================================
-- 🔄 ÍNDICES PARA SISTEMA CELERY
-- ============================================================================

-- Índices para celery_tasks
CREATE INDEX idx_celery_tasks_celery_id ON celery_tasks(celery_task_id);
CREATE INDEX idx_celery_tasks_user ON celery_tasks(user_id);
CREATE INDEX idx_celery_tasks_company ON celery_tasks(company_id);
CREATE INDEX idx_celery_tasks_status ON celery_tasks(status);
CREATE INDEX idx_celery_tasks_created ON celery_tasks(created_at DESC);
CREATE INDEX idx_celery_tasks_queue ON celery_tasks(queue_name, priority DESC);

-- Índices para celery_workers
CREATE INDEX idx_celery_workers_hostname ON celery_workers(hostname);
CREATE INDEX idx_celery_workers_status ON celery_workers(status);
CREATE INDEX idx_celery_workers_heartbeat ON celery_workers(last_heartbeat DESC);

-- ============================================================================
-- 📋 ÍNDICES PARA SISTEMA KANBAN
-- ============================================================================

-- Índices para kanban_boards
CREATE INDEX idx_kanban_boards_company ON kanban_boards(company_id);
CREATE INDEX idx_kanban_boards_created_by ON kanban_boards(created_by);

-- Índices para kanban_lists
CREATE INDEX idx_kanban_lists_board ON kanban_lists(board_id);
CREATE INDEX idx_kanban_lists_position ON kanban_lists(board_id, position);

-- Índices para kanban_cards
CREATE INDEX idx_kanban_cards_list ON kanban_cards(list_id);
CREATE INDEX idx_kanban_cards_assigned ON kanban_cards(assigned_to);
CREATE INDEX idx_kanban_cards_due_date ON kanban_cards(due_date);
CREATE INDEX idx_kanban_cards_position ON kanban_cards(list_id, position);

-- Índices para kanban_card_comments
CREATE INDEX idx_card_comments_card ON kanban_card_comments(card_id);
CREATE INDEX idx_card_comments_user ON kanban_card_comments(user_id);
CREATE INDEX idx_card_comments_created ON kanban_card_comments(created_at DESC);

-- ============================================================================
-- 📄 ÍNDICES PARA LICITAÇÕES E COTAÇÕES
-- ============================================================================

-- Índices para tenders
CREATE INDEX idx_tenders_company ON tenders(company_id);
CREATE INDEX idx_tenders_ai_status ON tenders(ai_processing_status);
CREATE INDEX idx_tenders_risk_score ON tenders(risk_score DESC);
CREATE INDEX idx_tenders_opportunity ON tenders(opportunity_score DESC);
CREATE INDEX idx_tenders_deadline ON tenders(submission_deadline);
CREATE INDEX idx_tenders_status ON tenders(status);
CREATE INDEX idx_tenders_created ON tenders(created_at DESC);

-- Índices para tender_ai_analyses
CREATE INDEX idx_tender_ai_analyses_tender ON tender_ai_analyses(tender_id);
CREATE INDEX idx_tender_ai_analyses_document ON tender_ai_analyses(document_id);
CREATE INDEX idx_tender_ai_analyses_type ON tender_ai_analyses(analysis_type);
CREATE INDEX idx_tender_ai_analyses_score ON tender_ai_analyses(overall_score DESC);

-- Índices para tender_items
CREATE INDEX idx_tender_items_tender ON tender_items(tender_id);
CREATE INDEX idx_tender_items_product ON tender_items(product_id);

-- Índices para suppliers
CREATE INDEX idx_suppliers_company ON suppliers(company_id);
CREATE INDEX idx_suppliers_cnpj ON suppliers(cnpj);
CREATE INDEX idx_suppliers_rating ON suppliers(rating DESC);

-- Índices para products
CREATE INDEX idx_products_company ON products(company_id);
CREATE INDEX idx_products_category ON products(category);

-- Índices para quotes
CREATE INDEX idx_quotes_tender ON quotes(tender_id);
CREATE INDEX idx_quotes_status ON quotes(status);
CREATE INDEX idx_quotes_created ON quotes(created_at DESC);

-- ============================================================================
-- 📅 ÍNDICES PARA CALENDÁRIO
-- ============================================================================

-- Índices para calendars
CREATE INDEX idx_calendars_company ON calendars(company_id);
CREATE INDEX idx_calendars_owner ON calendars(owner_id);

-- Índices para calendar_events
CREATE INDEX idx_calendar_events_start_time ON calendar_events(start_time);
CREATE INDEX idx_calendar_events_calendar ON calendar_events(calendar_id);
CREATE INDEX idx_calendar_events_tender ON calendar_events(tender_id);
CREATE INDEX idx_calendar_events_card ON calendar_events(kanban_card_id);

-- ============================================================================
-- 💬 ÍNDICES PARA MENSAGENS
-- ============================================================================

-- Índices para conversations
CREATE INDEX idx_conversations_company ON conversations(company_id);
CREATE INDEX idx_conversations_card ON conversations(kanban_card_id);
CREATE INDEX idx_conversations_tender ON conversations(tender_id);

-- Índices para messages
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_messages_created ON messages(created_at DESC);

-- ============================================================================
-- 🚨 ÍNDICES PARA AUDITORIA
-- ============================================================================

-- Índices para audit_logs
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_company ON audit_logs(company_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_category ON audit_logs(category, subcategory);
CREATE INDEX idx_audit_logs_severity ON audit_logs(severity);
CREATE INDEX idx_audit_logs_date ON audit_logs(date_only);
CREATE INDEX idx_audit_logs_review ON audit_logs(requires_review, reviewed_at);

-- Índices para security_alerts
CREATE INDEX idx_security_alerts_type ON security_alerts(alert_type);
CREATE INDEX idx_security_alerts_severity ON security_alerts(severity);
CREATE INDEX idx_security_alerts_status ON security_alerts(status);
CREATE INDEX idx_security_alerts_created ON security_alerts(created_at DESC);

-- ============================================================================
-- 🔍 ÍNDICES FULL-TEXT SEARCH
-- ============================================================================

-- Full-text search para licitações
CREATE INDEX idx_tenders_fulltext ON tenders USING gin(to_tsvector('portuguese', title || ' ' || COALESCE(description, '')));

-- Full-text search para documentos
CREATE INDEX idx_documents_fulltext ON documents USING gin(to_tsvector('portuguese', original_name));

-- Full-text search para kanban cards
CREATE INDEX idx_kanban_cards_fulltext ON kanban_cards USING gin(to_tsvector('portuguese', title || ' ' || COALESCE(description, '')));

-- Full-text search para fornecedores
CREATE INDEX idx_suppliers_fulltext ON suppliers USING gin(to_tsvector('portuguese', name || ' ' || COALESCE(contact_person, '')));

-- ============================================================================
-- 📊 ÍNDICES COMPOSTOS PARA QUERIES COMPLEXAS
-- ============================================================================

-- Índice composto para análise de licitações
CREATE INDEX idx_tenders_ai_composite ON tenders (company_id, ai_processing_status, risk_score DESC, submission_deadline);

-- Índice composto para processamento de documentos
CREATE INDEX idx_documents_processing_composite ON documents (company_id, processing_status, created_at DESC);

-- Índice composto para jobs de IA em fila
CREATE INDEX idx_ai_jobs_queue_composite ON ai_processing_jobs (status, priority DESC, created_at);

-- Índice composto para métricas temporais
CREATE INDEX idx_audit_logs_time_series ON audit_logs (company_id, created_at DESC, category);
CREATE INDEX idx_api_metrics_time_series ON api_metrics (date_only, endpoint, company_id);

-- Índice composto para sessões ativas
CREATE INDEX idx_sessions_active_only ON user_sessions (user_id, last_activity) WHERE is_active = true;

-- Índice composto para eventos de segurança não resolvidos
CREATE INDEX idx_security_events_unresolved ON security_events (created_at DESC) WHERE auto_resolved = false;

-- ============================================================================
-- 🎯 ÍNDICES PARCIAIS PARA OTIMIZAÇÃO
-- ============================================================================

-- Índices parciais para registros ativos
CREATE INDEX idx_users_active ON users (company_id, role) WHERE status = 'ACTIVE';
CREATE INDEX idx_suppliers_active ON suppliers (company_id, rating DESC) WHERE status = 'ACTIVE';
CREATE INDEX idx_tenders_active ON tenders (company_id, submission_deadline) WHERE status IN ('DRAFT', 'ANALYZING', 'READY');

-- Índices parciais para processamento
CREATE INDEX idx_documents_pending ON documents (company_id, created_at DESC) WHERE processing_status = 'PENDING';
CREATE INDEX idx_ai_jobs_running ON ai_processing_jobs (created_at DESC) WHERE status IN ('QUEUED', 'RUNNING');

-- Índices parciais para alertas
CREATE INDEX idx_alerts_active ON security_alerts (severity, created_at DESC) WHERE status = 'OPEN';
CREATE INDEX idx_metrics_alerts ON system_metrics (metric_type, created_at DESC) WHERE alert_triggered = true;

-- ============================================================================
-- 🛠️ CONFIGURAÇÕES DE PERFORMANCE
-- ============================================================================

-- Configurar autovacuum para tabelas com alta rotatividade
ALTER TABLE audit_logs SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE api_metrics SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE session_activities SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE file_access_logs SET (autovacuum_vacuum_scale_factor = 0.1);

-- Configurar fill factor para tabelas com muitas atualizações
ALTER TABLE user_sessions SET (fillfactor = 85);
ALTER TABLE rate_limit_tracking SET (fillfactor = 85);
ALTER TABLE system_metrics SET (fillfactor = 85);

-- ============================================================================
-- 📈 ESTATÍSTICAS E ANÁLISE
-- ============================================================================

-- Atualizar estatísticas para o otimizador
ANALYZE companies;
ANALYZE users;
ANALYZE user_sessions;
ANALYZE documents;
ANALYZE ai_processing_jobs;
ANALYZE tenders;
ANALYZE audit_logs;
ANALYZE api_metrics;
