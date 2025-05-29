#!/bin/bash
# Setup script for the tender platform backend

set -e

echo "🚀 Setting up Tender Platform Backend..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Create necessary directories
echo -e "${BLUE}📁 Creating necessary directories...${NC}"
mkdir -p logs/{nginx,app,celery}
mkdir -p backups/{postgres,mongodb,redis}
mkdir -p uploads
mkdir -p nginx/ssl

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚙️ Creating .env file from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️ Please update the .env file with your configuration before running the application.${NC}"
fi

# Generate secret key if needed
if grep -q "your-super-secret-key" .env; then
    echo -e "${BLUE}🔐 Generating secret key...${NC}"
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/your-super-secret-key-change-in-production-minimum-32-characters/$SECRET_KEY/g" .env
    echo -e "${GREEN}✅ Secret key generated and updated in .env${NC}"
fi

# Build and start services
echo -e "${BLUE}🐳 Building and starting Docker containers...${NC}"
docker-compose up -d --build

# Wait for services to be ready
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 30

# Check if Ollama is ready and pull model
echo -e "${BLUE}🤖 Setting up Ollama AI model...${NC}"
if docker-compose exec -T ollama ollama list | grep -q "llama3"; then
    echo -e "${GREEN}✅ Llama3 model already available${NC}"
else
    echo -e "${BLUE}📥 Pulling Llama3 model (this may take a while)...${NC}"
    docker-compose exec -T ollama ollama pull llama3:8b
fi

# Test Ollama
echo -e "${BLUE}🧪 Testing Ollama...${NC}"
if docker-compose exec -T ollama ollama run llama3:8b "Respond only with: OK" | grep -q "OK"; then
    echo -e "${GREEN}✅ Ollama is working correctly${NC}"
else
    echo -e "${YELLOW}⚠️ Ollama test failed, but continuing setup...${NC}"
fi

# Show service status
echo -e "${BLUE}📊 Service Status:${NC}"
docker-compose ps

# Show logs for any failed services
FAILED_SERVICES=$(docker-compose ps --services --filter "status=exited")
if [ ! -z "$FAILED_SERVICES" ]; then
    echo -e "${RED}❌ Some services failed to start:${NC}"
    for service in $FAILED_SERVICES; do
        echo -e "${RED}Failed service: $service${NC}"
        echo -e "${YELLOW}Logs:${NC}"
        docker-compose logs --tail=20 $service
    done
fi

echo ""
echo -e "${GREEN}🎉 Setup completed!${NC}"
echo ""
echo -e "${BLUE}📍 Service URLs:${NC}"
echo -e "  • Backend API: ${GREEN}http://localhost:8000${NC}"
echo -e "  • API Documentation: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  • PostgreSQL Admin: ${GREEN}http://localhost:8080${NC} (admin@admin.com / admin)"
echo -e "  • MongoDB Admin: ${GREEN}http://localhost:8082${NC} (admin / admin)"
echo -e "  • Redis Admin: ${GREEN}http://localhost:8081${NC}"
echo -e "  • Celery Monitor: ${GREEN}http://localhost:5555${NC}"
echo ""
echo -e "${BLUE}🔐 Default Login Credentials:${NC}"
echo -e "  • Admin: ${GREEN}admin@admin.com / admin123${NC}"
echo -e "  • Test User: ${GREEN}user@test.com / test123${NC}"
echo ""
echo -e "${BLUE}🛠️ Useful Commands:${NC}"
echo -e "  • View logs: ${YELLOW}docker-compose logs -f [service_name]${NC}"
echo -e "  • Stop services: ${YELLOW}docker-compose down${NC}"
echo -e "  • Restart services: ${YELLOW}docker-compose restart${NC}"
echo -e "  • Update services: ${YELLOW}docker-compose up -d --build${NC}"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
