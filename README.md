# CineBase 🎬

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)

A production-ready FastAPI backend for movie management with JWT authentication, role-based access control, and Redis caching.

## ✨ Features

- 🔐 JWT Authentication & Authorization
- 👥 User Registration & Role Management (User/Admin)
- 🎬 Movie CRUD Operations
- 📄 Pagination, Filtering & Sorting
- ⚡ Redis Caching
- 🗄️ PostgreSQL with Async SQLAlchemy
- 📚 Auto-generated OpenAPI Documentation
- 🧪 Comprehensive Test Suite
- 🐳 Docker & Docker Compose

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/Rokki-Khazratov/CineBase.git
cd CineBase

# Setup environment
cp .env.example .env
# Edit .env with your settings

# Start services
make up
make migrate

# Access API
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## 📖 API Examples

```bash
# Register user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'

# Get movies
curl -X GET "http://localhost:8000/api/v1/movies?limit=10&sort=year" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```


## 📚 Documentation
- [Architecture](docs/architecture.md) - System architecture and design
- [API Reference](http://localhost:8000/docs) - Interactive API documentation
- [Development Guide](docs/development.md) - Development setup and workflow
- [Deployment Guide](docs/deployment.md) - Production deployment



## 📄 License
MIT License - see [LICENSE](LICENSE) file.

## 👨‍💻 Author
**Rokki Khazratov** - [@Rokki-Khazratov](https://github.com/Rokki-Khazratov)
