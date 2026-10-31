# ABACUS v2.1 Deployment Package

## 📦 Contents

This deployment package contains everything needed to deploy ABACUS v2.1 to production:

### Core Files
- `README.md` - This file
- `Dockerfile` - Container configuration
- `docker-compose.yml` - Multi-container orchestration
- `.gitignore` - Git ignore rules

### Deployment Scripts
- `github_deployment_orchestrator.py` - Automates GitHub repository setup
- `local_deployment_runner.py` - Runs deployment locally for testing

### CI/CD
- `.github/workflows/ci-cd.yml` - GitHub Actions workflow

### Monitoring
- `monitoring/prometheus.yml` - Prometheus configuration

## 🚀 Quick Start

### Option 1: Deploy to GitHub
```bash
python github_deployment_orchestrator.py
# Follow instructions in GITHUB_DEPLOYMENT_INSTRUCTIONS.txt
```

### Option 2: Deploy Locally with Docker
```bash
python local_deployment_runner.py
# Access Grafana: http://localhost:3000
# Access Prometheus: http://localhost:9090
```

### Option 3: Manual Docker Deployment
```bash
docker build -t abacus-v21:latest .
docker-compose up -d
```

## 📋 Prerequisites

- Python 3.12+
- Git
- Docker & Docker Compose (for containerized deployment)
- GitHub account (for GitHub deployment)

## 🔧 Configuration

### Environment Variables
Create a `.env` file:
```
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

### Monitoring
- Prometheus scrapes metrics every 15s
- Grafana dashboards auto-configured
- Default credentials: admin/admin

## 📊 Deployment Options

### 1. GitHub + GitHub Actions
- Automated CI/CD pipeline
- Runs tests on every push
- Builds Docker images
- Deploys to production

### 2. Docker Compose
- Local development
- Testing environment
- Small-scale production

### 3. Cloud Platforms
- **Heroku**: `heroku container:push web`
- **AWS**: ECS/EKS deployment
- **Azure**: Container Instances
- **GCP**: Cloud Run

## 🧪 Testing

```bash
# Test Docker build
docker build -t abacus-v21:test .

# Test Docker run
docker run --rm abacus-v21:test python -c "print('OK')"

# Test compose
docker-compose config
docker-compose up --dry-run
```

## 📈 Monitoring

### Prometheus Metrics
- Application health
- Performance metrics
- Resource utilization

### Grafana Dashboards
- System overview
- Performance analytics
- Business metrics

## 🔐 Security

- Non-root container user
- Minimal base image
- No secrets in code
- Environment-based configuration

## 📝 Next Steps

1. ✅ Review deployment package
2. ⏳ Choose deployment option
3. ⏳ Run deployment script
4. ⏳ Verify deployment
5. ⏳ Set up monitoring
6. ⏳ Configure alerts

## 🆘 Troubleshooting

### Docker build fails
```bash
docker system prune -a
docker build --no-cache -t abacus-v21:latest .
```

### Port conflicts
```bash
# Change ports in docker-compose.yml
ports:
  - "3001:3000"  # Grafana
  - "9091:9090"  # Prometheus
```

### Permission issues
```bash
chmod +x *.py
sudo chown -R $USER:$USER .
```

## 📞 Support

- Documentation: See parent directory
- Issues: GitHub Issues
- Email: support@abacus-v21.example.com

---

**Version**: 2.1.0  
**Last Updated**: 2025-11-23  
**Status**: Production Ready
