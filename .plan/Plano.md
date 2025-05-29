    # Plano de Desenvolvimento - Sistema de Automação de Licitações

## 📋 Resumo Executivo

Sistema completo para automação do processo de participação em licitações, desde a extração de dados de editais até a consolidação final de cotações. Projeto full-stack com foco em aprendizado prático e evolução de habilidades técnicas.

## 🎯 Objetivos de Aprendizado

- **Backend:** FastAPI, PostgreSQL, MongoDB, Redis
- **Frontend:** React com Yarn
- **DevOps:** Docker, Docker Compose
- **IA/ML:** Integração com Ollama para processamento de documentos
- **Integrações:** APIs externas (Google Calendar, email)
- **Arquitetura:** Microsserviços e containerização

## 🏗️ Arquitetura do Sistema

### Stack Tecnológico
```
Frontend: React + TypeScript + Tailwind CSS
Backend: FastAPI + Python 3.13+
Bancos: PostgreSQL + MongoDB + Redis
IA: Ollama (local) ou OpenAI API
Deploy: Docker + Docker Compose
```

### Estrutura de Diretórios
```
├── .docs/                # Documentação do projeto
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints da API
│   │   ├── core/         # Configurações
│   │   ├── models/       # Modelos de dados
│   │   ├── services/     # Lógica de negócio
│   │   └── utils/        # Utilitários
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/   # Componentes React
│   │   ├── pages/        # Páginas principais
│   │   ├── hooks/        # Custom hooks
│   │   ├── services/     # Chamadas API
│   │   └── utils/        # Utilitários
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── docs/
```

## 📅 Cronograma de Desenvolvimento (20 semanas)

### Fase 1: Fundação e Páginas Públicas (Semanas 1-5)
**Semana 1-2: Setup e Landing Page**
- [ ] Configurar ambiente de desenvolvimento
- [ ] Setup Docker e Docker Compose
- [ ] Estrutura inicial do projeto
- [ ] Landing page responsiva com hero section
- [ ] Página institucional básica

**Semana 3: Página Demo Interativa**
- [ ] Demo funcional com dados mockados
- [ ] Simulação de upload e processamento
- [ ] Preview do fluxo completo
- [ ] Formulário de solicitação de acesso

**Semana 4-5: Core Backend e Banco**
- [ ] Modelos de dados completos (empresas, usuários, sessões)
- [ ] Configuração PostgreSQL e MongoDB
- [ ] API de solicitação de acesso (lead capture)
- [ ] Sistema de auditoria básico

### Fase 2: Autenticação e Controle de Acesso (Semanas 6-8)
**Semana 6-7: Sistema de Autenticação**
- [ ] JWT com refresh tokens
- [ ] **API Temporal para controle de sessões:**
  - Tokens com expiração dinâmica
  - Múltiplas sessões simultâneas
  - Auto-renovação de sessão ativa
  - Controle de timeout por inatividade
- [ ] Integração com Google OAuth
- [ ] Middleware de autenticação

**Semana 8: Hierarquia de Usuários**
- [ ] Sistema de roles e permissões
- [ ] Middleware de autorização
- [ ] Isolamento de dados por empresa
- [ ] Página secreta de admin master

### Fase 3: Área Master e Gestão de Empresas (Semanas 9-10)
**Semana 9: Painel Master**
- [ ] Interface administrativa master
- [ ] CRUD de empresas clientes
- [ ] Aprovação de solicitações de acesso
- [ ] Métricas globais do sistema

**Semana 10: Gestão de Usuários**
- [ ] Admin da empresa pode criar usuários
- [ ] Configurações por empresa
- [ ] Limites de uso por plano
- [ ] Dashboard de métricas por empresa

### Fase 4: Gestão de Fornecedores (Semanas 11-12)
- [ ] Modelo de dados para fornecedores (isolado por empresa)
- [ ] API CRUD fornecedores com isolamento
- [ ] Associação fornecedor-produto
- [ ] Sistema de filtros e busca avançada
- [ ] Interface frontend completa

### Fase 5: Processamento de Editais (Semanas 13-15)
**Semana 13-14: Upload e Parsing**
- [ ] Sistema de upload multi-formato com validação
- [ ] Integração com Ollama para extração
- [ ] Parser robusto para diferentes formatos
- [ ] Preview e validação de dados extraídos

**Semana 15: IA e Análise**
- [ ] Prompts otimizados para extração semântica
- [ ] Sistema de análise de riscos
- [ ] Interface de correção manual
- [ ] Cache inteligente com Redis

### Fase 6: Sistema de Cotações (Semanas 16-17)
**Semana 16: Geração de Cotações**
- [ ] Templates personalizáveis por empresa
- [ ] Seleção automática de fornecedores
- [ ] Interface colaborativa de edição
- [ ] Sistema de aprovação interna

**Semana 17: Envio e Monitoramento**
- [ ] Sistema de envio multi-canal (email, WhatsApp)
- [ ] Tracking detalhado de respostas
- [ ] Lembretes automáticos configuráveis
- [ ] Dashboard em tempo real

### Fase 7: Integrações e Relatórios (Semanas 18-19)
**Semana 18: Integrações**
- [ ] Google Calendar com OAuth 2.0
- [ ] Sincronização de prazos e eventos
- [ ] Notificações push/email
- [ ] API de webhooks para integrações

**Semana 19: Relatórios e Analytics**
- [ ] Consolidação automática de cotações
- [ ] Geração de planilhas avançadas (XLSX/CSV)
- [ ] Relatórios gerenciais por empresa
- [ ] Métricas de performance e ROI

### Fase 8: Finalização e Deploy (Semana 20)
- [ ] Testes de integração end-to-end
- [ ] Testes de carga e performance
- [ ] Documentação completa da API
- [ ] Deploy em produção com monitoramento
- [ ] Treinamento de usuários master

## 🗄️ Modelo de Dados

### PostgreSQL (Dados Relacionais)
```sql
-- Empresas/Organizações
companies (
  id, 
  name, 
  cnpj, 
  email, 
  phone, 
  address, 
  plan_type, 
  status, 
  created_at, 
  updated_at
)

-- Usuários com hierarquia
users (
  id, 
  company_id, 
  email, 
  password_hash, 
  first_name, 
  last_name, 
  role, -- MASTER, ADMIN_EMPRESA, USUARIO, VIEWER
  status, -- ACTIVE, INACTIVE, PENDING
  last_login,
  created_at, 
  updated_at
)

-- Sessões e controle temporal
user_sessions (
  id,
  user_id,
  token_hash,
  ip_address,
  user_agent,
  expires_at,
  last_activity,
  is_active,
  created_at
)

-- Solicitações de acesso (lead generation)
access_requests (
  id,
  company_name,
  cnpj,
  contact_name,
  email,
  phone,
  message,
  status, -- PENDING, CONTACTED, CONVERTED, REJECTED
  source, -- DEMO, LANDING, REFERRAL
  created_at
)

-- Fornecedores (por empresa)
suppliers (
  id, 
  company_id, -- FK para isolamento por empresa
  name, 
  email, 
  phone, 
  address, 
  lead_time, 
  commercial_conditions, 
  created_at
)

-- Produtos
products (id, name, description, category, unit, created_at)

-- Associação fornecedor-produto
supplier_products (supplier_id, product_id, price, availability)

-- Editais (por empresa)
tenders (
  id, 
  company_id, -- FK para isolamento
  number, 
  object, 
  deadline, 
  risk_score, 
  status, 
  file_path, 
  created_by, -- user_id
  created_at
)

-- Itens do edital
tender_items (id, tender_id, description, quantity, unit, specifications)

-- Cotações
quotes (id, tender_id, supplier_id, status, sent_at, response_at, total_value)

-- Itens da cotação
quote_items (id, quote_id, tender_item_id, unit_price, total_price, delivery_time)

-- Auditoria de ações
audit_log (
  id,
  user_id,
  company_id,
  action,
  entity_type,
  entity_id,
  old_values,
  new_values,
  ip_address,
  created_at
)
```

### MongoDB (Logs e Chat)
```javascript
// Logs de atividades
activity_logs: {
  user_id: ObjectId,
  action: String,
  entity_type: String,
  entity_id: String,
  details: Object,
  timestamp: Date
}

// Histórico de processamento IA
ai_processing: {
  tender_id: String,
  file_path: String,
  extracted_data: Object,
  confidence_score: Number,
  processing_time: Number,
  timestamp: Date
}
```

## 🔧 Sistema de Autenticação Temporal (API Temporal)

### Conceito da API Temporal
Sistema avançado de gerenciamento de sessões que vai além do JWT tradicional:

#### Características Principais:
```python
# Estrutura de Sessão Temporal
session = {
    "token_id": "uuid4",
    "user_id": "user_uuid", 
    "expires_at": "timestamp",
    "last_activity": "timestamp",
    "auto_renew": True,
    "max_idle_time": 1800,  # 30 min
    "max_session_time": 28800,  # 8 horas
    "device_fingerprint": "hash",
    "ip_address": "x.x.x.x",
    "is_mobile": False,
    "concurrent_limit": 3
}
```

#### Funcionalidades Avançadas:
1. **Renovação Inteligente:**
   - Auto-renova tokens antes da expiração
   - Ajusta tempo baseado na atividade do usuário
   - Diferentes tempos para mobile vs desktop

2. **Controle de Concorrência:**
   - Limite de sessões simultâneas por usuário
   - Controle por dispositivo/localização
   - Força logout de sessões antigas

3. **Análise de Comportamento:**
   - Detecta padrões suspeitos de uso
   - Força re-autenticação em mudanças de IP
   - Log detalhado de todas as atividades

4. **Gestão Dinâmica:**
   - Sessões mais longas para usuários ativos
   - Timeout agressivo para dados sensíveis
   - Configuração por role/empresa

### Implementação da API Temporal:
```python
# Middleware de Sessão Temporal
class TemporalSessionMiddleware:
    async def __call__(self, request, call_next):
        # Validar token
        # Verificar última atividade
        # Auto-renovar se necessário
        # Atualizar fingerprint
        # Log da atividade
        pass

# Endpoints específicos
POST /auth/temp/extend     # Extensão manual de sessão
GET  /auth/temp/status     # Status da sessão atual
POST /auth/temp/refresh    # Refresh inteligente
GET  /auth/temp/activity   # Histórico de atividades
```

### Endpoints Backend
```python
# Páginas Públicas (sem auth)
GET    /api/public/demo-data          # Dados para página demo
POST   /api/public/access-request     # Solicitação de acesso
GET    /api/public/plans              # Planos disponíveis

# Autenticação com API Temporal
POST   /auth/login                    # Login tradicional
POST   /auth/google                   # Login com Google
POST   /auth/refresh                  # Renovar token
POST   /auth/logout                   # Logout e invalidar sessão
GET    /auth/sessions                 # Listar sessões ativas
DELETE /auth/sessions/{session_id}    # Encerrar sessão específica
GET    /auth/validate                 # Validar token atual

# Master Admin (Super Admin)
GET    /api/master/companies          # Listar todas empresas
POST   /api/master/companies          # Cadastrar nova empresa
PUT    /api/master/companies/{id}     # Editar empresa
GET    /api/master/stats              # Métricas globais
GET    /api/master/access-requests    # Solicitações pendentes
PUT    /api/master/access-requests/{id} # Aprovar/rejeitar

# Admin Empresa
GET    /api/admin/users               # Usuários da empresa
POST   /api/admin/users               # Criar usuário
PUT    /api/admin/users/{id}          # Editar usuário
DELETE /api/admin/users/{id}          # Desativar usuário
GET    /api/admin/company-stats       # Métricas da empresa

# Fornecedores (isolado por empresa)
GET    /api/suppliers                 # Fornecedores da empresa
POST   /api/suppliers                 # Criar fornecedor
GET    /api/suppliers/{id}
PUT    /api/suppliers/{id}
DELETE /api/suppliers/{id}

# Editais (isolado por empresa)
POST   /api/tenders/upload
GET    /api/tenders                   # Editais da empresa
GET    /api/tenders/{id}
POST   /api/tenders/{id}/process

# Cotações (isolado por empresa)
POST   /api/quotes/generate
GET    /api/quotes
POST   /api/quotes/{id}/send
GET    /api/quotes/{id}/status

# Relatórios
GET    /api/reports/consolidation/{tender_id}
POST   /api/reports/export

# Auditoria
GET    /api/audit/logs                # Logs da empresa
GET    /api/master/audit/global       # Logs globais (só master)
```

## 🎨 Interface do Usuário

### Estrutura de Páginas e Níveis de Acesso

#### 🌐 Páginas Públicas (Sem Autenticação)
1. **Landing Page (/):** 
   - Hero section com proposta de valor
   - Demonstração de funcionalidades
   - Depoimentos e cases de sucesso
   - CTA para cadastro/demo

2. **Página Institucional (/sobre):**
   - História da empresa/projeto
   - Missão, visão e valores
   - Equipe e contatos
   - Certificações e compliance

3. **Página Demo (/demo):**
   - Simulação interativa do sistema
   - Upload de edital exemplo
   - Visualização do processo completo
   - Formulário para solicitar acesso

4. **Solicitar Acesso (/cadastro):**
   - Formulário de interesse comercial
   - Dados da empresa interessada
   - Planos e preços
   - Agendamento de apresentação

#### 🔐 Autenticação e Onboarding
5. **Login/Autenticação (/auth):**
   - Login tradicional (email/senha)
   - Integração com Google/Microsoft
   - Recuperação de senha
   - **API Temporal para controle de sessões:**
     - Tokens JWT com expiração dinâmica
     - Renovação automática de sessão
     - Controle de múltiplas sessões simultâneas
     - Log de atividades por sessão

#### 👥 Área de Usuários Padrão (Pós-login)
6. **Dashboard:** Visão geral de editais ativos e cotações
7. **Fornecedores:** Gestão do cadastro de fornecedores
8. **Editais:** Upload, processamento e análise
9. **Cotações:** Geração, edição e envio
10. **Relatórios:** Consolidação e exportação
11. **Agenda:** Integração com Google Calendar
12. **Perfil:** Configurações da conta e empresa

#### 🔧 Área Master (Super Admin)
13. **Admin Master (/master):**
    - **Acesso via URL secreta + autenticação especial**
    - Painel de controle de todas as empresas
    - Cadastro de novas empresas clientes
    - Gestão de planos e limites de uso
    - Métricas globais do sistema
    - Configurações de sistema

### Hierarquia de Usuários
```
MASTER (Super Admin)
├── Pode cadastrar empresas
├── Acesso a todas as empresas
├── Configurações globais
└── Métricas consolidadas

ADMIN_EMPRESA (Admin da Empresa)
├── Gestão de usuários da empresa
├── Configurações da empresa
├── Acesso a todos os dados da empresa
└── Relatórios gerenciais

USUARIO (Usuário Padrão)
├── Acesso aos módulos operacionais
├── CRUD de fornecedores
├── Processamento de editais
└── Geração de cotações

VIEWER (Apenas Visualização)
├── Acesso somente leitura
├── Visualização de relatórios
└── Exportação de dados
```

### Componentes Reutilizáveis
- **LandingComponents:** Hero, Features, Testimonials, Pricing
- **AuthComponents:** LoginForm, SignupForm, PasswordReset
- **DataTable:** Paginação, filtros e ordenação avançada
- **FileUploader:** Multi-formato com preview
- **FormBuilder:** Formulários dinâmicos e validação
- **StatusBadge:** Estados com cores semânticas
- **ChartComponents:** Visualizações de dados
- **AccessControl:** Wrapper para controle de permissões

## 🚀 Estratégia de Deploy

### Desenvolvimento Local
```bash
# Clone e setup
git clone <repo>
docker-compose up -d

# Acesso
Frontend: http://localhost:3000
Backend: http://localhost:8000
Docs: http://localhost:8000/docs
```

### Produção (Opções)
1. **VPS Tradicional:** Docker Compose + Nginx
2. **Cloud Native:** AWS ECS + RDS + S3
3. **Híbrida:** DigitalOcean App Platform

## 📊 Métricas de Sucesso

### Técnicas
- [ ] Cobertura de testes > 80%
- [ ] Tempo de resposta API < 200ms
- [ ] Uptime > 99%
- [ ] Documentação completa

### Funcionais
- [ ] Upload de 5+ formatos de documento
- [ ] Extração automática com 90%+ precisão
- [ ] Envio de cotações em < 5 minutos
- [ ] Integração completa com calendário

## 🛡️ Considerações de Segurança

- Autenticação JWT com refresh tokens
- Validação rigorosa de uploads
- Rate limiting em APIs críticas
- Logs de auditoria completos
- Backup automático de dados

## 📚 Recursos de Aprendizado

### Documentação Essencial
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
- [Docker Compose](https://docs.docker.com/compose/)
- [PostgreSQL Tutorial](https://www.postgresql.org/docs/)

### Cursos Recomendados
- FastAPI do zero (YouTube)
- React Hooks avançado
- Docker para desenvolvedores
- PostgreSQL performance

## 🎯 Próximos Passos

1. **Setup Imediato:**
   - Criar repositório Git
   - Configurar ambiente local
   - Implementar hello world em ambas as pontas

2. **Primeira Sprint (Semana 1):**
   - Docker Compose funcional
   - Conexão banco de dados
   - Primeira API endpoint
   - Primeiro componente React

3. **Validação Rápida:**
   - Upload simples de arquivo
   - Listagem básica de dados
   - Teste de integração frontend/backend

---
## 📝 Conclusão