-- ============================================================================
-- 📊 SISTEMA DE NEGÓCIOS - LICITAÇÕES, KANBAN, FORNECEDORES
-- ============================================================================

-- ============================================================================
-- 📝 SISTEMA DE FORMULÁRIOS
-- ============================================================================

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
    reviewed_by UUID REFERENCES users(id)
);

-- ============================================================================
-- 📋 SISTEMA KANBAN
-- ============================================================================

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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Comentários nos cards
CREATE TABLE kanban_card_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID NOT NULL REFERENCES kanban_cards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    content TEXT NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Membros dos boards
CREATE TABLE kanban_board_members (
    board_id UUID NOT NULL REFERENCES kanban_boards(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'MEMBER', -- OWNER, ADMIN, MEMBER, VIEWER
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (board_id, user_id)
);

-- ============================================================================
-- 🏢 SISTEMA DE FORNECEDORES E PRODUTOS
-- ============================================================================

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

-- ============================================================================
-- 📄 SISTEMA DE LICITAÇÕES E COTAÇÕES (APRIMORADO COM IA)
-- ============================================================================

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
    
    CONSTRAINT tenders_company_number_unique UNIQUE (company_id, number)
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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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

-- ============================================================================
-- 📅 SISTEMA DE CALENDÁRIO
-- ============================================================================

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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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
