# 🎯 **Bug Hunt Guide - Kairos**

*How to use bug hunting tools to improve code quality*

---

## 🚀 **Quick Start**

### 1. Install dependencies

```bash
# Install the project dependencies
make install

# Install the bug hunting tools (already included in requirements.txt)
pip install ruff bandit safety pytest pytest-cov
```

### 2. Run a full analysis

```bash
# Method 1: Use the main script
./scripts/bug_hunt.sh --full --report

# Method 2: Use the Makefile
make bug-hunt-full

# Method 3: Run manually
./scripts/bug_hunt.sh --security --lint --test --duplicate --report
```

### 3. View the results

All reports are generated in the `reports/` directory:
- `bandit-results.json` - Security analysis results
- `safety-results.json` - Dependency vulnerabilities
- `ruff-results.json` - Linter errors
- `duplicates-results.txt` - Duplicate code
- `bug-hunt-report-*.md` - Full report

---

## 🛠️ **Available Commands**

### **Full Analysis**

| Command | Description | Duration |
|----------|-------------|-------|
| `make bug-hunt-full` | Runs all checks | ~5-10 min |
| `./scripts/bug_hunt.sh --full` | Same, with more options | ~5-10 min |
| `make all` | Tests + Linting + Formatting + Security | ~5 min |

### **Analysis by Category**

#### **Security**
```bash
# Full security analysis
make bug-hunt-security
./scripts/bug_hunt.sh --security

# Bandit only (static code analysis)
bandit -r app/ -f json -o reports/bandit-results.json

# Safety only (dependency vulnerabilities)
safety check --json --output reports/safety-results.json
```

#### **Code Quality**
```bash
# Linter check
make bug-hunt-lint
./scripts/bug_hunt.sh --lint
ruff check app/ --output-file=reports/ruff-results.json

# Formatting check
make format
black --check . --exclude=".git|__pycache__|instance|venv"

# Fix formatting
make format-fix
black . --exclude=".git|__pycache__|instance|venv"
```

#### **Tests**
```bash
# Run all tests
make bug-hunt-tests
./scripts/bug_hunt.sh --test
python -m pytest tests/ -v --tb=short

# Tests with coverage
make test-coverage
python -m pytest tests/ --cov=app --cov=config --cov-report=html

# Quick tests
make test-quick
python -m pytest tests/ --tb=no -q
```

#### **Duplicate Code**
```bash
# Search for duplicate code
make bug-hunt-duplicates
./scripts/bug_hunt.sh --duplicate
python scripts/find_duplicates.py --check-imports

# Full search (includes similar code)
python scripts/find_duplicates.py --check-imports --check-similar
```

### **Quick Analysis**

```bash
# Security + Linter (fast)
make bug-hunt-quick
./scripts/bug_hunt.sh --quick

# Generate a report
make bug-hunt-report
./scripts/bug_hunt.sh --full --report
```

---

## 📊 **Interpreting the Results**

### **Overall Score**

The `bug_hunt.sh` script calculates an overall score based on:

| Criterion | Weight | Impact on Score |
|---------|--------|---------------------|
| Security (Bandit) | 40% | -10 points per issue |
| Security (Safety) | 40% | -10 points per vulnerability |
| Linter (Ruff) | 30% | -15 points if errors |
| Tests | 20% | -20 points if failures |
| Duplicate Code | 10% | -10 points if duplication |

**Score:**
- 90-100: A ✅ Excellent
- 80-89: B ✅ Good
- 70-79: C ⚠️ Average
- 60-69: D ⚠️ Needs improvement
- 0-59: F ❌ Critical

### **Severity Levels**

| Level | Color | Description | Action |
|--------|---------|-------------|--------|
| 🔴 Critical | Red | Blocking issues | Fix IMMEDIATELY |
| 🟡 Medium | Yellow | Important issues | Fix quickly |
| 🟢 Low | Green | Minor issues | Fix if possible |

---

## 🎯 **Fixing Issues**

### **1. Duplicate Code**

#### **Problem:** Duplicate `_make_cache_key` functions

**Files:**
- `app/utils/cache.py:732`
- `app/utils/optimizations.py:125, 218`

**Solution:**
```python
# Create a new file: app/utils/cache_helpers.py

def make_cache_key(f: Callable, args: tuple, kwargs: dict, 
                  key_prefix: str = '', vary_on: Optional[list] = None) -> str:
    """Unified function to generate cache keys."""
    import hashlib
    from flask import current_app
    from flask_login import current_user
    
    key_parts = [f.__module__, f.__name__]
    
    if key_prefix:
        key_parts.insert(0, key_prefix)
    
    if vary_on:
        for arg_name in vary_on:
            if arg_name in kwargs:
                key_parts.append(str(kwargs[arg_name]))
    else:
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        key_parts.append(f"user_id={current_user.id}")
    
    key_string = ':'.join(key_parts)
    return hashlib.sha256(key_string.encode('utf-8')).hexdigest()
```

**Then replace in all files:**
```python
# Before
from app.utils.cache import _make_cache_key

# After
from app.utils.cache_helpers import make_cache_key
```

#### **Problem:** Duplicate `get_bool` and `get_int` functions

**Files:** 4 different files

**Solution:**
```python
# Create: app/utils/env_helpers.py

def get_bool(env_var: str, default: bool = False) -> bool:
    """Retrieve a boolean environment variable."""
    import os
    value = os.environ.get(env_var, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

def get_int(env_var: str, default: int = 0) -> int:
    """Retrieve an integer environment variable."""
    import os
    try:
        return int(os.environ.get(env_var, str(default)))
    except ValueError:
        return default
```

### **2. Security Issues**

#### **Problem:** Weak default secret key

**File:** `config.py`

**Solution:**
```python
# Before
SECRET_KEY = os.environ.get("SECRET_KEY") or "ta-cle-secrete-ici"

# After
import secrets
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
```

#### **Problem:** CSRF disabled

**File:** `config.py`

**Solution:**
```python
# In ProductionConfig
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
```

#### **Problem:** Authentication can be disabled

**File:** `config.py`

**Solution:**
```python
# Remove or comment out
# LOGIN_DISABLED = get_bool_from_env("LOGIN_DISABLED", False)
```

### **3. Linter Errors**

#### **Problem:** Unused imports

**File:** `app/__init__.py`

**Solution:**
```python
# Before
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
import sqlite3
import logging
from logging.handlers import RotatingFileHandler, SysLogHandler
import os
import traceback
import re
from datetime import datetime

# After
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import logging
import os
```

#### **Problem:** Single quotes

**Solution:** Replace all single quotes with double quotes:
```bash
# Use a replacement script
find app/ -name "*.py" -exec sed -i 's/'\''/"/g' {} \;
# Then manually fix the cases where single quotes are required
```

### **4. Failed Tests**

#### **Problem:** Missing `create_app` function

**File:** `app/__init__.py`

**Solution:**
```python
# Add at the end of app/__init__.py
def create_app(config_object="config.Config"):
    """Factory function to create and configure the Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_object)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Initialize the cache
    init_cache(app)
    
    # Import routes
    from app.routes import main, admin, export, auth
    app.register_blueprint(main.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(export.bp)
    app.register_blueprint(auth.bp)
    
    return app
```

---

## 📈 **Best Practices**

### **1. Writing Maintainable Code**

✅ **Do:**
- Use clear function and variable names
- Comment complex code
- Avoid duplicate code (DRY principle)
- Keep functions short (< 50 lines)

❌ **Avoid:**
- Duplicate code
- Overly long functions
- Unnecessary comments
- Ambiguous variable names

### **2. Security**

✅ **Do:**
- Always validate user input
- Use strong passwords
- Encrypt sensitive data
- Limit permissions

❌ **Avoid:**
- Plaintext passwords
- Secret keys in code
- Blind trust in user input
- Disabling security protections

### **3. Tests**

✅ **Do:**
- Test positive and negative cases
- Test edge cases
- Maintain good coverage (> 80%)
- Run tests regularly

❌ **Avoid:**
- Tests that depend on execution order
- Overly slow tests
- Tests that don't test anything

---

## 🔧 **Automation**

### **1. Continuous Integration (CI)**

Create a `.github/workflows/bug-hunt.yml` file:

```yaml
name: Bug Hunt

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  bug-hunt:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run Bug Hunt
      run: |
        ./scripts/bug_hunt.sh --full --report
    
    - name: Upload reports
      uses: actions/upload-artifact@v3
      with:
        name: bug-hunt-reports
        path: reports/
```

### **2. Pre-commit Hooks**

Create a `.pre-commit-config.yaml` file:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.18
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  
  - repo: https://github.com/psf/black-pre-commit
    rev: 26.5.1
    hooks:
      - id: black
        language_version: python3.12
  
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

Install the hooks:
```bash
pip install pre-commit
pre-commit install
```

---

## 📚 **Resources**

### **Documentation**
- [Full Bug Hunt Report](BUG_HUNT_REPORT.md)
- [Bug Hunt Summary](BUG_HUNT_SUMMARY.md)
- [Security Audit Report](SECURITY_AUDIT_REPORT.md)
- [Testing Summary](TESTING_SUMMARY.md)

### **Tools**
- [Ruff](https://docs.astral.sh/ruff/) - Fast linter
- [Bandit](https://bandit.readthedocs.io/) - Security analysis
- [Safety](https://getsafety.com/) - Dependency vulnerabilities
- [pytest](https://docs.pytest.org/) - Testing framework
- [Black](https://black.readthedocs.io/) - Code formatter

### **Best Practices**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Python Security](https://wiki.python.org/moin/Security)
- [12 Factor App](https://12factor.net/)

---

## 🎉 **Bug Hunt Checklist**

- [ ] Run `make bug-hunt-full`
- [ ] Fix critical issues (🔴)
- [ ] Fix medium issues (🟡)
- [ ] Fix minor issues (🟢)
- [ ] Verify that all tests pass
- [ ] Reach 80%+ coverage
- [ ] Run a new security audit
- [ ] Document the fixes
- [ ] Update the bug hunt report

---

*"Code quality is everyone's responsibility." - Kent Beck*

*Guide automatically generated by Vibe Code - Bug Hunting Agent*
