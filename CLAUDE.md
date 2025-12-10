# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Developer Profile

**Experience Level:** 10+ years Full Stack Developer
**Specializations:**
- Kubernetes Administrator (CKA certified level)
- DevSecOps practices
- Python, Go, JavaScript/React, Bash
- Infrastructure as Code, CI/CD pipelines

## Mandatory Development Practices

### DevSecOps Requirements (STRICT)

Every code change MUST follow this checklist before commit:

1. **Code Scan** - Run security and static analysis
   ```bash
   # Python
   bandit -r src/
   safety check

   # JavaScript
   npm audit

   # General
   trivy fs .
   ```

2. **Unit Tests** - All new code must have tests
   ```bash
   pytest tests/ --cov=src --cov-report=term-missing
   npm run test
   ```

3. **Linting & Formatting**
   ```bash
   # Python
   black . && isort . && pylint src/
   mypy src/

   # JavaScript
   npm run lint && npm run format
   ```

4. **Local Git Commit** - All changes tracked locally
   ```bash
   git add .
   git commit -m "descriptive message"
   ```

### Critical Rules

- **NEVER** introduce code that breaks existing functionality
- **ALWAYS** understand existing code before modifying
- **ALWAYS** run tests before and after changes
- **ALWAYS** update ROADMAP.md and TASKS.md after completing work
- **ALWAYS** scan code for vulnerabilities before commit
- **NEVER** commit secrets, tokens, or credentials

## Document Tracking (MANDATORY)

### ROADMAP.md
- Contains project milestones and high-level progress
- Update after completing major features
- Mark completed items with `[x]` and ✅

### TASKS.md
- Contains granular task checklist
- Update as tasks are started/completed
- Track blockers and dependencies

## Related SBOM Projects

This project is part of a larger SBOM ecosystem at `~/projects/`:

| Project | Type | Purpose |
|---------|------|---------|
| **sbomapp** | FastAPI + React | SBOMly web platform (my.sbomly.com) |
| **ai_sbom** | Go CLI | AI-enhanced SBOM with Claude API |
| **embedded_sbom** | Python | Embedded C/C++ SBOM generator |
| **sbom** | Python/Bash | SBOM toolkit with vulnerability scanning |

### Cross-Project Awareness

When working on this project, be aware of:
- Shared patterns from `sbom/` (HTML report generation, vulnerability scanning)
- API patterns from `sbomapp/` (FastAPI, async processing)
- CLI patterns from `ai_sbom/` (Go CLI structure, Syft/Grype integration)

## Kubernetes Context

As a CKA-level administrator, apply these practices:

- Design for containerization (12-factor app principles)
- Use ConfigMaps and Secrets for configuration
- Implement health checks (liveness/readiness probes)
- Design for horizontal scaling (stateless where possible)
- Consider resource limits and requests
- Use namespaces for environment separation

## Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/description

# 2. Write code with tests
# 3. Run security scan
bandit -r src/ && safety check

# 4. Run tests
pytest tests/ -v

# 5. Format and lint
black . && isort . && pylint src/

# 6. Commit locally
git add . && git commit -m "feat: description"

# 7. Update tracking docs
# Edit ROADMAP.md and TASKS.md

# 8. Final verification
pytest tests/ && bandit -r src/
```

## Code Quality Gates

Before ANY commit:
- [ ] Security scan passes (bandit, safety, trivy)
- [ ] All tests pass
- [ ] No regressions in existing functionality
- [ ] Code formatted and linted
- [ ] ROADMAP.md updated (if milestone)
- [ ] TASKS.md updated

## Environment Setup

```bash
# Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Development dependencies
pip install pytest pytest-cov black isort pylint mypy bandit safety

# Initialize git
git init
git add .
git commit -m "Initial commit"
```

## Architecture Principles

1. **Separation of Concerns** - Clear module boundaries
2. **Defensive Coding** - Validate inputs, handle errors gracefully
3. **Immutable Infrastructure** - Design for containers/K8s
4. **Security First** - Scan early, scan often
5. **Test Coverage** - Minimum 80% coverage target
6. **Documentation** - Code is self-documenting, but complex logic needs comments

## Memory/Context Awareness

**CRITICAL:** Before writing new code:
1. Review what has been written in this session
2. Understand dependencies between components
3. Verify new code won't break existing functionality
4. Run tests to confirm no regressions
5. Document any architectural decisions

This ensures continuity and prevents breaking changes across the development session.
