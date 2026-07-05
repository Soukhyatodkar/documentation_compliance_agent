# Deployment Guide

> **Complete deployment instructions for production and development environments**

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Deployment](#cloud-deployment)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Environment Configuration](#environment-configuration)
6. [Monitoring & Logging](#monitoring--logging)
7. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- pip or poetry
- Git
- Docker (for Qdrant)

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/documentation-compliance-agent.git
cd documentation-compliance-agent
```

### Step 2: Create Virtual Environment

```bash
# Using venv
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using poetry
poetry install
poetry shell
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development tools

# Install Playwright browsers
playwright install chromium
```

### Step 4: Start Qdrant Vector Database

```bash
# Option 1: Docker (recommended)
docker run -p 6333:6333 qdrant/qdrant:latest

# Option 2: Docker Compose
docker-compose -f docker/docker-compose.yml up -d

# Option 3: Download Qdrant standalone (https://qdrant.tech/documentation/quick-start/)
```

### Step 5: Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit with your values
nano .env
```

**.env file:**
```bash
OPENAI_API_KEY=sk-your-key-here
QDRANT_URL=http://localhost:6333
WEBSITE_URL=https://your-website.com
WEBSITE_USERNAME=your_username
WEBSITE_PASSWORD=your_password
```

### Step 6: Verify Setup

```bash
# Test configuration
python main.py validate-config

# Test connections
python main.py test-connection

# Run health check
python main.py health-check
```

### Step 7: Run the Agent

```bash
# Full pipeline
python main.py run --config config/base_config.yaml

# Or individual stages
python main.py ingest
python main.py extract
python main.py compare
python main.py report
```

---

## Docker Deployment

### Single Container

**1. Build Image**

```bash
docker build -f docker/Dockerfile -t compliance-agent:latest .

# With tag
docker build -f docker/Dockerfile -t compliance-agent:1.0.0 .
```

**2. Run Container**

```bash
docker run \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config \
  --name compliance-agent \
  compliance-agent:latest
```

**3. Monitor Logs**

```bash
# View logs
docker logs compliance-agent

# Follow logs
docker logs -f compliance-agent

# View specific container
docker ps | grep compliance-agent
```

### Docker Compose Stack

**1. Start Full Stack**

```bash
# Start Qdrant + Agent
docker-compose -f docker/docker-compose.yml up -d

# View services
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f
```

**2. Configuration for Docker Compose**

**.env file:**
```bash
QDRANT_API_KEY=your-api-key-if-secured
OPENAI_API_KEY=sk-your-key
QDRANT_URL=http://qdrant:6333  # Use service name
```

**3. Stop Stack**

```bash
docker-compose -f docker/docker-compose.yml down

# Remove volumes
docker-compose -f docker/docker-compose.yml down -v
```

### Docker Network

For multi-container communication:

```bash
# Create network
docker network create compliance-network

# Run Qdrant on network
docker run \
  --network compliance-network \
  --name qdrant \
  -p 6333:6333 \
  qdrant/qdrant:latest

# Run agent on same network
docker run \
  --network compliance-network \
  --env QDRANT_URL=http://qdrant:6333 \
  compliance-agent:latest
```

---

## Cloud Deployment

### AWS Deployment

**Option 1: AWS Lambda**

```python
# lambda_handler.py
import asyncio
from src.cli.commands import run_compliance_pipeline

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    config_path = event.get('config_path', 'config/base_config.yaml')
    
    try:
        result = asyncio.run(run_compliance_pipeline(config_path))
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

**Option 2: AWS ECS Fargate**

```yaml
# ecs-task-definition.json
{
  "family": "compliance-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "compliance-agent",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/compliance-agent:latest",
      "environment": [
        {"name": "QDRANT_URL", "value": "http://qdrant:6333"},
        {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/compliance-agent",
          "awslogs-region": "YOUR_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

**Deploy:**
```bash
# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com
docker tag compliance-agent:latest YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/compliance-agent:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/compliance-agent:latest

# Update ECS service
aws ecs update-service --cluster compliance-cluster --service compliance-service --force-new-deployment
```

### Google Cloud Platform

**Cloud Run:**

```bash
# Build and deploy to Cloud Run
gcloud run deploy compliance-agent \
  --source . \
  --region us-central1 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --set-env-vars "QDRANT_URL=http://qdrant:6333" \
  --set-env-vars "OPENAI_API_KEY=sk-..."
```

### Azure Deployment

**Container Instances:**

```bash
# Create resource group
az group create --name compliance-rg --location eastus

# Deploy container
az container create \
  --resource-group compliance-rg \
  --name compliance-agent \
  --image compliance-agent:latest \
  --cpu 2 \
  --memory 4 \
  --environment-variables QDRANT_URL=http://qdrant:6333
```

---

## CI/CD Pipeline

### GitHub Actions

**File:** `.github/workflows/ci.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
      
      - name: Lint
        run: |
          black --check src tests
          isort --check src tests
          flake8 src tests
      
      - name: Type check
        run: mypy src
      
      - name: Run tests
        run: pytest tests/ --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -f docker/Dockerfile -t compliance-agent:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker tag compliance-agent:${{ github.sha }} ${{ secrets.DOCKER_USERNAME }}/compliance-agent:latest
          docker push ${{ secrets.DOCKER_USERNAME }}/compliance-agent:latest
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          # Your deployment commands
          echo "Deploying to production..."
```

### Pre-commit Hooks

**File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

**Install:**
```bash
pre-commit install
pre-commit run --all-files
```

---

## Environment Configuration

### Development Environment

**.env.development:**
```bash
# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=json

# Services
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=sk-dev-key

# Website
WEBSITE_URL=https://staging.example.com
SKIP_EXTRACTION=false

# Performance
CONCURRENT_WORKERS=2
BATCH_SIZE=10

# Output
OUTPUT_BASE_DIR=./data/dev
KEEP_SCREENSHOTS=true
```

### Staging Environment

**.env.staging:**
```bash
LOG_LEVEL=INFO
QDRANT_URL=http://qdrant.staging.internal:6333
OPENAI_API_KEY=${AWS_SECRETS_OPENAI_KEY}
WEBSITE_URL=https://staging.example.com
CONCURRENT_WORKERS=4
BATCH_SIZE=50
OUTPUT_BASE_DIR=/var/data/staging
```

### Production Environment

**.env.production:**
```bash
LOG_LEVEL=WARN
QDRANT_URL=http://qdrant.prod.internal:6333
OPENAI_API_KEY=${AWS_SECRETS_OPENAI_KEY}
WEBSITE_URL=https://example.com
SKIP_EXTRACTION=false
CONCURRENT_WORKERS=8
BATCH_SIZE=100
OUTPUT_BASE_DIR=/var/data/production
ENABLE_MONITORING=true
SENTRY_DSN=${SENTRY_DSN}
```

---

## Monitoring & Logging

### Structured Logging

**Configuration:**
```yaml
logging:
  level: INFO
  format: json  # or text
  handlers:
    - console     # stdout
    - file        # /var/logs/app.log
    - syslog      # Remote logging
    - sentry      # Error tracking
  
  filters:
    - min_level: CRITICAL  # Send only critical to Sentry
    - sampling_rate: 0.1   # Log 10% of INFO events
```

**Log Output:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "src.agent.compliance_agent",
  "event": "comparison_complete",
  "component_id": "comp_001",
  "discrepancies": 2,
  "confidence": 0.95,
  "duration_ms": 1250
}
```

### Metrics & Monitoring

**Prometheus Metrics:**
```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
comparisons_total = Counter('comparisons_total', 'Total comparisons')
comparison_duration = Histogram('comparison_duration_seconds', 'Comparison duration')
discrepancies_found = Gauge('discrepancies_found', 'Current discrepancies')

# Usage
with comparison_duration.time():
    assessment = agent.assess_compliance(component)
comparisons_total.inc()
```

**Grafana Dashboard:**
```json
{
  "dashboard": {
    "title": "Compliance Agent Metrics",
    "panels": [
      {
        "title": "Comparisons per minute",
        "targets": [{"expr": "rate(comparisons_total[1m])"}]
      },
      {
        "title": "Average comparison duration",
        "targets": [{"expr": "histogram_quantile(0.95, comparison_duration_seconds)"}]
      },
      {
        "title": "Discrepancies found",
        "targets": [{"expr": "discrepancies_found"}]
      }
    ]
  }
}
```

### Error Tracking

**Sentry Integration:**
```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0,
    environment=os.getenv("ENVIRONMENT", "development")
)

# Errors automatically sent to Sentry
try:
    result = agent.assess_compliance(component)
except Exception as e:
    sentry_sdk.capture_exception(e)
    raise
```

---

## Troubleshooting

### Qdrant Connection Issues

**Error:** `Connection refused to Qdrant at http://localhost:6333`

**Solutions:**
```bash
# Check if Qdrant is running
curl http://localhost:6333/health

# Start Qdrant if not running
docker run -p 6333:6333 qdrant/qdrant:latest

# Check firewall
sudo ufw allow 6333

# Verify environment variable
echo $QDRANT_URL
```

### OpenAI API Errors

**Error:** `Invalid API key`

**Solutions:**
```bash
# Verify API key
echo $OPENAI_API_KEY

# Test API connectivity
python -c "import openai; openai.api_key='$OPENAI_API_KEY'; print(openai.Model.list())"

# Check rate limits
# Visit: https://platform.openai.com/account/rate-limits

# Common fixes:
# 1. API key expired - regenerate in OpenAI dashboard
# 2. Rate limit exceeded - add delay and retry
# 3. Wrong model name - check config
```

### Memory Issues

**Error:** `MemoryError` or `Out of memory`

**Solutions:**
```bash
# Increase batch size
batch_size: 10  # Reduce from 50

# Reduce concurrent workers
concurrent_workers: 2  # Reduce from 8

# Increase container memory
docker run -m 8g compliance-agent:latest

# Monitor memory
docker stats compliance-agent
```

### Slow Performance

**Diagnosis:**
```bash
# Check logs for bottlenecks
grep "duration" logs/app.log | sort -t= -k2 -rn

# Monitor Qdrant
curl http://localhost:6333/collections

# Check network latency
ping $(echo $QDRANT_URL | cut -d/ -f3)
```

**Optimization:**
```bash
# Enable caching
caching:
  enabled: true
  ttl: 3600

# Increase batch size
batch_size: 100

# Add more concurrent workers
concurrent_workers: 8

# Use CDN for embeddings
embeddings:
  cache_dir: /var/cache/embeddings
```

### Database Issues

**Lost data in Qdrant:**
```bash
# Backup before deletion
docker exec qdrant tar czf /backup/snapshot.tar.gz /qdrant/storage

# Recreate collection
python -c "
from src.vector_store.qdrant_client import QdrantVectorStore
vs = QdrantVectorStore(config)
vs.create_collection()  # Recreates
"

# Restore from backup if needed
docker exec qdrant tar xzf /backup/snapshot.tar.gz -C /
```

---

## Rollback Procedures

### Database Rollback

```bash
# Create backup before updates
docker run -v qdrant_storage:/data -v $(pwd)/backups:/backup \
  ubuntu tar czf /backup/qdrant_$(date +%s).tar.gz /data

# Restore if needed
docker run -v qdrant_storage:/data -v $(pwd)/backups:/backup \
  ubuntu tar xzf /backup/qdrant_TIMESTAMP.tar.gz -C /
```

### Application Rollback

```bash
# With Docker
docker stop compliance-agent
docker run --name compliance-agent -d compliance-agent:v1.0.0

# With Kubernetes
kubectl rollout undo deployment/compliance-agent

# Manual
git checkout v1.0.0
pip install -r requirements.txt
python main.py run
```

---

## Performance Tuning

### Configuration for Scale

**High-volume audit:**
```yaml
app:
  concurrent_workers: 16
  batch_size: 200

vector_db:
  search_limit: 10
  batch_insert_size: 500

llm:
  concurrent_calls: 20
  timeout: 120
  retry_count: 5

browser:
  headless: true
  disable_images: true
  parallel_tabs: 4
```

---

## Related Documentation

- [README.md](../README.md) - Quick start
- [CONFIGURATION.md](CONFIGURATION.md) - Config options
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design

---

**Deployment Version:** 1.0  
**Last Updated:** December 2024  
**Status:** Production Ready

