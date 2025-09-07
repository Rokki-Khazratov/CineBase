# Deployment Guide

## 🚀 Production Deployment

### Prerequisites

- Docker & Docker Compose
- Domain name (optional)
- SSL certificate (for HTTPS)
- Production database
- Redis instance

## 🐳 Docker Deployment

### 1. Build Production Image

```bash
# Build image
docker build -t cinebase:latest .

# Tag for registry
docker tag cinebase:latest your-registry/cinebase:latest

# Push to registry
docker push your-registry/cinebase:latest
```

### 2. Production Environment

```bash
# Create production .env
cp .env.example .env.prod

# Edit production settings
nano .env.prod
```

### 3. Production Configuration

```bash
# .env.prod
APP_ENV=prod
APP_HOST=0.0.0.0
APP_PORT=8000
APP_NAME=CineBase
APP_VERSION=1.0.0

# Security
SECRET_KEY=your-very-secure-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=15

# Database
DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/cinebase

# Cache
REDIS_URL=redis://redis-host:6379/0

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Logging
LOG_LEVEL=INFO
```

### 4. Run Production Container

```bash
# Run with production settings
docker run -d \
  --name cinebase \
  -p 8000:8000 \
  --env-file .env.prod \
  --restart unless-stopped \
  cinebase:latest
```

## 🐳 Docker Compose Production

### docker-compose.prod.yml

```yaml
version: "3.8"

services:
  api:
    image: cinebase:latest
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=prod
      - DATABASE_URL=postgresql+asyncpg://cinebase:${DB_PASSWORD}@db:5432/cinebase
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: cinebase
      POSTGRES_USER: cinebase
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cinebase"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Deploy with Compose

```bash
# Create production environment file
echo "SECRET_KEY=your-secret-key" > .env.prod
echo "DB_PASSWORD=your-db-password" >> .env.prod

# Deploy
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
```

## 🌐 Nginx Configuration

### nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /docs {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## ☁️ Cloud Deployment

### AWS ECS

```yaml
# task-definition.json
{
  "family": "cinebase",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions":
    [
      {
        "name": "cinebase",
        "image": "your-account.dkr.ecr.region.amazonaws.com/cinebase:latest",
        "portMappings": [{ "containerPort": 8000, "protocol": "tcp" }],
        "environment":
          [
            { "name": "APP_ENV", "value": "prod" },
            {
              "name": "DATABASE_URL",
              "value": "postgresql+asyncpg://user:pass@rds-endpoint:5432/cinebase",
            },
            {
              "name": "REDIS_URL",
              "value": "redis://elasticache-endpoint:6379/0",
            },
          ],
        "secrets":
          [
            {
              "name": "SECRET_KEY",
              "valueFrom": "arn:aws:secretsmanager:region:account:secret:cinebase/secret-key",
            },
          ],
        "logConfiguration":
          {
            "logDriver": "awslogs",
            "options":
              {
                "awslogs-group": "/ecs/cinebase",
                "awslogs-region": "us-east-1",
                "awslogs-stream-prefix": "ecs",
              },
          },
      },
    ],
}
```

### Google Cloud Run

```yaml
# cloudbuild.yaml
steps:
  - name: "gcr.io/cloud-builders/docker"
    args: ["build", "-t", "gcr.io/$PROJECT_ID/cinebase:$COMMIT_SHA", "."]
  - name: "gcr.io/cloud-builders/docker"
    args: ["push", "gcr.io/$PROJECT_ID/cinebase:$COMMIT_SHA"]
  - name: "gcr.io/cloud-builders/gcloud"
    args:
      - "run"
      - "deploy"
      - "cinebase"
      - "--image"
      - "gcr.io/$PROJECT_ID/cinebase:$COMMIT_SHA"
      - "--region"
      - "us-central1"
      - "--platform"
      - "managed"
      - "--allow-unauthenticated"
      - "--set-env-vars"
      - "APP_ENV=prod,DATABASE_URL=postgresql+asyncpg://user:pass@/cloudsql/project:region:instance/cinebase,REDIS_URL=redis://redis-ip:6379/0"
      - "--set-secrets"
      - "SECRET_KEY=secret-key:latest"
```

### Heroku

```bash
# Create Heroku app
heroku create cinebase-api

# Set environment variables
heroku config:set APP_ENV=prod
heroku config:set SECRET_KEY=your-secret-key
heroku config:set DATABASE_URL=postgresql://user:pass@host:5432/db
heroku config:set REDIS_URL=redis://user:pass@host:6379/0

# Deploy
git push heroku main

# Run migrations
heroku run alembic upgrade head
```

## 🔒 Security Configuration

### SSL/TLS

```bash
# Generate self-signed certificate (dev only)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Use Let's Encrypt for production
certbot --nginx -d yourdomain.com
```

### Environment Security

```bash
# Use strong secret key
SECRET_KEY=$(openssl rand -hex 32)

# Use strong database password
DB_PASSWORD=$(openssl rand -base64 32)

# Restrict CORS origins
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Database Security

```sql
-- Create dedicated user
CREATE USER cinebase WITH PASSWORD 'strong-password';

-- Grant minimal permissions
GRANT CONNECT ON DATABASE cinebase TO cinebase;
GRANT USAGE ON SCHEMA public TO cinebase;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cinebase;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cinebase;
```

## 📊 Monitoring & Logging

### Application Logs

```bash
# View logs
docker logs cinebase

# Follow logs
docker logs -f cinebase

# Log aggregation with ELK stack
# Configure logstash to collect Docker logs
```

### Health Monitoring

```bash
# Health check endpoint
curl https://yourdomain.com/api/v1/health

# Set up monitoring alerts
# Use tools like Prometheus + Grafana
```

### Database Monitoring

```sql
-- Monitor connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'cinebase';

-- Monitor slow queries
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

## 🔄 Backup & Recovery

### Database Backup

```bash
# Create backup
docker exec cinebase_db pg_dump -U cinebase cinebase > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker exec -i cinebase_db psql -U cinebase cinebase < backup_20240101_120000.sql

# Automated backups
# Add to crontab
0 2 * * * docker exec cinebase_db pg_dump -U cinebase cinebase > /backups/backup_$(date +\%Y\%m\%d_\%H\%M\%S).sql
```

### Redis Backup

```bash
# Create Redis backup
docker exec cinebase_redis redis-cli BGSAVE

# Copy backup file
docker cp cinebase_redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d_%H%M%S).rdb
```

## 🚨 Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs
docker logs cinebase

# Check environment variables
docker exec cinebase env

# Check health status
docker inspect cinebase | grep Health
```

#### Database Connection Issues

```bash
# Test database connection
docker exec cinebase_db psql -U cinebase -d cinebase -c "SELECT 1;"

# Check database logs
docker logs cinebase_db

# Verify network connectivity
docker exec cinebase ping db
```

#### Performance Issues

```bash
# Check resource usage
docker stats

# Monitor database performance
docker exec cinebase_db psql -U cinebase -d cinebase -c "SELECT * FROM pg_stat_activity;"

# Check Redis memory usage
docker exec cinebase_redis redis-cli info memory
```

### Recovery Procedures

#### Application Recovery

```bash
# Restart application
docker restart cinebase

# Scale up if needed
docker-compose up -d --scale api=3
```

#### Database Recovery

```bash
# Restore from backup
docker exec -i cinebase_db psql -U cinebase cinebase < backup.sql

# Recreate database
docker-compose down
docker volume rm cinebase_postgres_data
docker-compose up -d
```

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale API instances
docker-compose up -d --scale api=3

# Use load balancer
# Configure nginx upstream with multiple API instances
```

### Database Scaling

```bash
# Read replicas
# Configure PostgreSQL streaming replication
# Use connection pooling (PgBouncer)
```

### Cache Scaling

```bash
# Redis Cluster
# Configure Redis Sentinel for high availability
# Use Redis Cluster for horizontal scaling
```

## 🔄 CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build and push Docker image
        run: |
          docker build -t cinebase:latest .
          docker tag cinebase:latest ${{ secrets.REGISTRY }}/cinebase:latest
          docker push ${{ secrets.REGISTRY }}/cinebase:latest

      - name: Deploy to production
        run: |
          ssh ${{ secrets.SERVER_USER }}@${{ secrets.SERVER_HOST }} '
            docker pull ${{ secrets.REGISTRY }}/cinebase:latest
            docker-compose -f docker-compose.prod.yml up -d
            docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
          '
```

## 📚 Additional Resources

- [Docker Production Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Nginx Configuration Guide](https://nginx.org/en/docs/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Redis Production Deployment](https://redis.io/docs/management/deployment/)
- [SSL/TLS Configuration](https://ssl-config.mozilla.org/)
