# 🚀 Tender Platform Backend

A comprehensive, scalable, and modular backend system for automating tender processes using FastAPI, SQLAlchemy, MongoDB, Redis, and AI integration with Ollama/LLaMA 3.

## 🏗️ Architecture Overview

This backend follows a **Modularized Monolith** pattern with clear separation of concerns:

- **Entry Layer**: FastAPI routers (`app/api/`)
- **Application Layer**: Business services (`app/services/`)
- **Domain Layer**: Schemas and business logic (`app/schemas/`, `app/models/`)
- **Infrastructure Layer**: Database, external integrations (`app/db/`, `app/tasks/`)

## 🛠️ Tech Stack

### Core Framework
- **FastAPI** 0.110+ - Modern, fast web framework
- **Python** 3.11+ - Latest stable Python version
- **Uvicorn/Gunicorn** - ASGI server with worker processes

### Databases
- **PostgreSQL** 15+ - Primary relational database
- **MongoDB** 7+ - Document storage for flexible data
- **Redis** 7+ - Caching and session storage

### AI & Processing
- **Ollama** - Local LLM inference server
- **LLaMA 3** - Open-source language model
- **Celery** - Distributed task queue for AI processing

### Additional Services
- **Alembic** - Database migrations
- **Pydantic** - Data validation and serialization
- **Motor** - Async MongoDB driver
- **aioredis** - Async Redis client

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Git

### 1. Clone and Setup
```bash
git clone <repository-url>
cd backend
cp .env.example .env
# Edit .env with your configuration
```

### 2. Run Setup Script
```bash
chmod +x setup.sh
./setup.sh
```

### 3. Access Services
- **API Documentation**: http://localhost:8000/docs
- **Backend API**: http://localhost:8000
- **PostgreSQL Admin**: http://localhost:8080
- **MongoDB Admin**: http://localhost:8082
- **Redis Admin**: http://localhost:8081
- **Celery Monitor**: http://localhost:5555

## 🔧 Manual Setup (Alternative)

### 1. Environment Configuration
```bash
cp .env.example .env
# Edit .env file with your settings
```

### 2. Start Services
```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Run Database Migrations
```bash
docker-compose exec backend alembic upgrade head
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/     # API endpoints
│   ├── core/                 # Core configuration
│   ├── crud/                 # Database operations
│   ├── db/                   # Database setup and models
│   ├── middleware/           # Custom middleware
│   ├── schemas/              # Pydantic schemas
│   ├── services/             # Business logic
│   ├── tasks/                # Background tasks
│   ├── utils/                # Utility functions
│   └── websockets/           # Real-time communication
├── alembic/                  # Database migrations
├── scripts/                  # Utility scripts
├── tests/                    # Test suite
├── docker-compose.yml        # Development environment
├── docker-compose.prod.yml   # Production environment
├── Dockerfile                # Container definition
└── README.md                 # This file
```

## 🔑 Default Credentials

### Admin User
- **Email**: admin@admin.com
- **Password**: admin123

### Test User
- **Email**: user@test.com
- **Password**: test123

### Database Admin Interfaces
- **pgAdmin**: admin@admin.com / admin
- **Mongo Express**: admin / admin

## 🧪 Development

### Running Tests
```bash
docker-compose exec backend pytest
```

### Code Quality
```bash
# Format code
docker-compose exec backend black .
docker-compose exec backend isort .

# Lint code
docker-compose exec backend flake8
docker-compose exec backend mypy app
```

### Database Operations
```bash
# Create migration
docker-compose exec backend alembic revision --autogenerate -m "Migration name"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback migration
docker-compose exec backend alembic downgrade -1
```

### Logs
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f celery_worker
docker-compose logs -f postgres
```

## 🔌 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Current user info

### Companies
- `GET /api/v1/companies/` - List companies
- `POST /api/v1/companies/` - Create company
- `GET /api/v1/companies/{id}` - Get company
- `PUT /api/v1/companies/{id}` - Update company

### Users
- `GET /api/v1/users/` - List users
- `POST /api/v1/users/` - Create user
- `GET /api/v1/users/{id}` - Get user
- `PUT /api/v1/users/{id}` - Update user

### Tenders
- `GET /api/v1/tenders/` - List tenders
- `POST /api/v1/tenders/` - Create tender
- `GET /api/v1/tenders/{id}` - Get tender
- `PUT /api/v1/tenders/{id}` - Update tender
- `POST /api/v1/tenders/{id}/process-ai` - AI processing

### Suppliers & Quotes
- `GET /api/v1/suppliers/` - List suppliers
- `POST /api/v1/suppliers/` - Create supplier
- `GET /api/v1/quotes/` - List quotes
- `POST /api/v1/quotes/` - Create quote

### Kanban
- `GET /api/v1/kanban/boards/` - List boards
- `POST /api/v1/kanban/boards/` - Create board
- `GET /api/v1/kanban/cards/` - List cards
- `POST /api/v1/kanban/cards/` - Create card

## 🤖 AI Features

### Document Processing
- Automatic text extraction from PDFs
- Tender information analysis
- Risk assessment
- Quote structure generation

### Supported File Types
- PDF documents
- Word documents (.doc, .docx)
- Excel files (.xls, .xlsx)
- Text files (.txt)

### AI Models
- **Default**: LLaMA 3 8B (CPU/GPU compatible)
- **Advanced**: LLaMA 3 70B (GPU required)

## 🔄 Background Tasks

### Celery Workers
- AI document processing
- Email notifications
- File processing
- Calendar synchronization
- Automated reminders

### Task Monitoring
Access Flower dashboard at http://localhost:5555 to monitor:
- Active tasks
- Task history
- Worker status
- Queue statistics

## 📊 Monitoring & Health Checks

### Health Endpoints
- `GET /health` - General health check
- `GET /health/db` - Database connectivity
- `GET /health/ai` - AI service status
- `GET /health/redis` - Redis connectivity

### Logging
- Structured JSON logging
- Request/response logging
- Error tracking
- Performance metrics

## 🔒 Security Features

### Authentication
- JWT-based authentication
- Refresh token rotation
- Session management
- Multi-device support

### Rate Limiting
- API rate limiting
- IP-based restrictions
- User-based quotas
- Adaptive thresholds

### Data Protection
- Password hashing (bcrypt)
- SQL injection prevention
- XSS protection
- CORS configuration

## 🚀 Production Deployment

### Environment Variables
Copy and configure production environment:
```bash
cp .env.example .env.prod
# Configure production settings
```

### Production Deployment
```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Performance Tuning
- PostgreSQL optimization
- Redis memory configuration
- Gunicorn worker tuning
- Nginx reverse proxy

## 📦 Backup & Recovery

### Automated Backups
```bash
# Manual backup
./scripts/backup.sh

# Automated daily backups (configured in docker-compose)
```

### Backup Contents
- PostgreSQL database dump
- MongoDB collections
- Redis data snapshots
- File uploads

### Recovery
```bash
# Restore PostgreSQL
docker-compose exec postgres psql -U postgres -d tender_platform < backup.sql

# Restore MongoDB
docker-compose exec mongodb mongorestore --drop backup/

# Restore Redis
docker-compose exec redis redis-cli --rdb backup.rdb
```

## 🐛 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker-compose logs [service_name]

# Rebuild containers
docker-compose down
docker-compose up -d --build
```

#### Database Connection Error
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready

# Reset database
docker-compose down -v
docker-compose up -d
```

#### AI Service Issues
```bash
# Check Ollama status
docker-compose exec ollama ollama list

# Pull model manually
docker-compose exec ollama ollama pull llama3:8b
```

### Performance Issues
- Monitor resource usage: `docker stats`
- Check service logs: `docker-compose logs -f`
- Review application metrics in Flower

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

### Code Standards
- Follow PEP 8 style guide
- Write comprehensive tests
- Document all functions
- Use type hints

### Testing
```bash
# Run full test suite
pytest

# Run specific tests
pytest tests/api/test_auth.py

# Coverage report
pytest --cov=app tests/
```

## 📚 Documentation

### API Documentation
- Interactive docs: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

### Database Schema
- ERD available in `/docs/database-schema.png`
- Migration history in `/alembic/versions/`

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation

---

**Built with ❤️ using FastAPI, SQLAlchemy, and modern Python practices**
