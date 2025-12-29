# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## #1 Rule (ABSOLUTE)

**Add features and fixes WITHOUT breaking existing behavior.**

You are my coding partner. This is non-negotiable.

---

## Developer Profile

**Experience Level:** 10+ years Full Stack Developer
**Specializations:**
- Kubernetes Administrator (CKA certified level)
- DevSecOps practices
- Python, Go, JavaScript/React, Bash
- Infrastructure as Code, CI/CD pipelines

---

## Operating Rules

### Branch Policy
- **Work ONLY on the `dev` branch**
- **NEVER commit to main/master**

### Before Starting ANY Work
Read and align with:
- `ROADMAP.md` / `ROADMAP_TASKS.md`
- `CHANGE_LOG.md`
- ALL markdown files in the project

### Core Principles
- **No refactoring or restructuring** unless explicitly required by the task
- **No hardcoding** - paths, secrets, IDs, env-specific values must use config/env/constants
- **Keep changes minimal** and localized to what's needed for the task
- **NEVER introduce code that breaks existing functionality**
- **ALWAYS understand existing code before modifying**
- **NEVER commit secrets, tokens, or credentials**

---

## Code Structure Rules

### Modularity & Separation of Concerns
- Write modular code with clear separation of concerns
- Each module/component should have a **single responsibility**
- Use **dependency injection**; avoid tight coupling between modules
- Define clear **interfaces/contracts** between modules (so they can become separate services later)

### Architecture Boundaries
- Keep business logic **independent of infrastructure** (database, APIs, frameworks)
- Structure code so modules can be **tested, replaced, or extracted** independently
- **No cross-module access** to internal implementation details—use public interfaces only
- If building toward microservices: identify bounded contexts and keep cross-module communication through well-defined APIs/events, not direct imports of internals

### Design Principles
1. **Separation of Concerns** - Clear module boundaries
2. **Defensive Coding** - Validate inputs, handle errors gracefully
3. **Immutable Infrastructure** - Design for containers/K8s
4. **Security First** - Scan early, scan often
5. **Test Coverage** - Minimum 80% coverage target
6. **Documentation** - Code is self-documenting, but complex logic needs comments

---

## Public API / Schema Safety (MUST FOLLOW)

- **Do NOT change public APIs, contracts, schemas, or output formats** unless explicitly approved
- If a public API/schema change is unavoidable:
  1. **Call it out clearly**
  2. **Propose a backward-compatible approach** (versioning, deprecation, feature flag, optional fields)
  3. **Update docs + changelog**
  4. **Add migration notes** if needed

---

## Testing Rules

### Before Coding
- Run (or specify) the relevant existing unit/integration tests to establish a **baseline**

### When Adding Features
- Add/extend tests and include them in the test suite

### When Fixing Bugs
- Add a **regression test** that fails before the fix and passes after

### After Every Change
Run:
1. The existing test suite
2. The existing regression test suite
3. Any new tests you added

**If any test fails, fix it before moving forward.**

```bash
# Run tests with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Verify no regressions
pytest tests/ -v
```

---

## DevSecOps Requirements (STRICT)

Every code change MUST follow this checklist before commit:

### 1. Security Scans (SCA, SAST)
```bash
# Python SAST
bandit -r src/

# Dependency vulnerability scan (SCA)
safety check

# General filesystem scan
trivy fs .
```

### 2. SBOM Generation
```bash
# Generate SBOM report under reports/ folder
syft . -o cyclonedx-json > reports/sbom.json
```

### 3. Vulnerability Scanning
```bash
# Scan for vulnerabilities
grype sbom:reports/sbom.json -o json > reports/vulnerabilities.json
```

### 4. Unit Tests
```bash
pytest tests/ --cov=src --cov-report=term-missing --cov-report=html:reports/coverage
```

### 5. Linting & Formatting
```bash
# Python
black . && isort . && pylint src/
mypy src/
```

### 6. HTML Reports
All scan results should be output to `reports/` folder in HTML format where possible.

---

## Safe-Change Checklist (DO THIS EVERY TIME)

1. **Restate** what you're about to change and why
2. **Identify** impacted codepaths and risks
3. **Implement** in small steps
4. **Verify** behavior with tests (existing + new) and targeted checks

---

## Progress & Documentation

After every feature/fix:
- [ ] Update project docs/progress notes
- [ ] Update `CHANGE_LOG.md` with a concise entry
- [ ] Update `TASKS.md` / task list if applicable
- [ ] Update `ROADMAP.md` if milestone completed

---

## Branching / Promotion Flow (STOP POINTS REQUIRED)

```
1. Implement changes on dev
2. Commit changes and push to dev
3. Run automated tests + regression tests
4. ⛔ STOP and wait for approval (manual testing/review)
5. After approval: push to staging
6. Run staging regression tests
7. If all pass: promote to production
```

**Never skip the approval gate.**

---

## Output Format for Every Response

Use this structure for all responses:

```
## Plan
[What you're going to do and why]

## Files to Change
[List of files that will be modified/created]

## Patch / Code
[The actual code changes]

## Tests (existing run + new/updated)
[Test commands and results]

## Commands to Run
[All commands needed]

## API/Schema Impact Check
[Any public API or schema changes - if none, state "None"]

## Risk Notes
[Potential risks or side effects]

## What I Need From You (Approval Gate)
[What approval is needed before proceeding]
```

---

## Code Quality Gates

Before ANY commit:
- [ ] Security scan passes (bandit, safety, trivy)
- [ ] All tests pass
- [ ] No regressions in existing functionality
- [ ] Code formatted and linted
- [ ] SBOM generated
- [ ] Vulnerability scan completed
- [ ] CHANGE_LOG.md updated
- [ ] ROADMAP.md updated (if milestone)
- [ ] TASKS.md updated

---

## Document Tracking (MANDATORY)

### ROADMAP.md
- Contains project milestones and high-level progress
- Update after completing major features
- Mark completed items with `[x]`

### TASKS.md
- Contains granular task checklist
- Update as tasks are started/completed
- Track blockers and dependencies

### CHANGE_LOG.md
- Concise entry for every change
- Format: `[date] - [type] - [description]`

---

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

---

## Kubernetes Context

As a CKA-level administrator, apply these practices:

- Design for containerization (12-factor app principles)
- Use ConfigMaps and Secrets for configuration
- Implement health checks (liveness/readiness probes)
- Design for horizontal scaling (stateless where possible)
- Consider resource limits and requests
- Use namespaces for environment separation

---

## Environment Setup

```bash
# Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Development dependencies
pip install pytest pytest-cov black isort pylint mypy bandit safety

# Verify on dev branch
git checkout dev
```

---

## Memory/Context Awareness

**CRITICAL:** Before writing new code:
1. Review what has been written in this session
2. Understand dependencies between components
3. Verify new code won't break existing functionality
4. Run tests to confirm no regressions
5. Document any architectural decisions

This ensures continuity and prevents breaking changes across the development session.
