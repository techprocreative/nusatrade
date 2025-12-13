#!/usr/bin/env python3
"""
Production startup validation script.

This script validates all production requirements before starting the application.
Run this before deployment to ensure everything is configured correctly.
"""

import os
import sys
from pathlib import Path

# Color codes for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'


class ValidationError(Exception):
    """Validation failed."""
    pass


def print_header(text: str):
    """Print section header."""
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}{text:^60}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}\n")


def print_check(name: str, passed: bool, message: str = ""):
    """Print validation check result."""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"  [{status}] {name}")
    if message:
        prefix = "      " if passed else f"      {YELLOW}"
        suffix = "" if passed else RESET
        print(f"{prefix}{message}{suffix}")


def check_environment():
    """Check environment variable."""
    env = os.getenv('ENVIRONMENT', 'development')
    is_prod = env.lower() == 'production'

    print_check(
        "Environment setting",
        is_prod,
        f"Current: {env} (must be 'production')"
    )

    if not is_prod:
        raise ValidationError("ENVIRONMENT must be set to 'production'")


def check_required_env_vars():
    """Check all required environment variables."""
    required_vars = {
        'DATABASE_URL': 'Database connection string',
        'REDIS_URL': 'Redis connection string',
        'JWT_SECRET': 'JWT secret key (min 32 chars)',
        'SETTINGS_ENCRYPTION_KEY': 'Settings encryption key',
        'FRONTEND_URL': 'Frontend URL for emails/redirects',
        'BACKEND_CORS_ORIGINS': 'Allowed CORS origins',
    }

    all_passed = True

    for var, description in required_vars.items():
        value = os.getenv(var)
        exists = value is not None and value.strip() != ""

        # Additional validation for specific vars
        if var == 'JWT_SECRET' and exists:
            if len(value) < 32:
                print_check(var, False, f"Too short ({len(value)} chars, need 32+)")
                all_passed = False
                continue

        if var in ['DATABASE_URL', 'REDIS_URL', 'FRONTEND_URL'] and exists:
            if 'localhost' in value or '127.0.0.1' in value:
                print_check(var, False, f"Contains localhost - use production service!")
                all_passed = False
                continue

        print_check(var, exists, description)
        if not exists:
            all_passed = False

    if not all_passed:
        raise ValidationError("Missing or invalid required environment variables")


def check_optional_env_vars():
    """Check optional but recommended environment variables."""
    optional_vars = {
        'LLM_API_KEY': 'AI/LLM API key (for trading insights)',
        'SENDGRID_API_KEY': 'Email service API key',
        'SENTRY_DSN': 'Error tracking (Sentry)',
    }

    for var, description in optional_vars.items():
        value = os.getenv(var)
        exists = value is not None and value.strip() != ""
        print_check(var, exists, f"{description} {'(configured)' if exists else '(not configured)'}")


def check_database_connection():
    """Check database connectivity."""
    try:
        from sqlalchemy import create_engine, text

        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            raise ValidationError("DATABASE_URL not set")

        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        print_check("Database connection", True, "Successfully connected")

    except Exception as e:
        print_check("Database connection", False, f"Error: {str(e)}")
        raise ValidationError(f"Database connection failed: {e}")


def check_redis_connection():
    """Check Redis connectivity."""
    try:
        import redis

        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            raise ValidationError("REDIS_URL not set")

        client = redis.from_url(redis_url)
        client.ping()

        print_check("Redis connection", True, "Successfully connected")

    except Exception as e:
        print_check("Redis connection", False, f"Error: {str(e)}")
        raise ValidationError(f"Redis connection failed: {e}")


def check_directories():
    """Check required directories exist."""
    required_dirs = [
        'models/staging',
        'models/production',
        'models/archive',
        'migrations/versions',
    ]

    all_passed = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        exists = path.exists() and path.is_dir()
        print_check(f"Directory: {dir_path}", exists)
        if not exists:
            # Try to create it
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"      {GREEN}Created directory{RESET}")
            except Exception as e:
                print(f"      {RED}Failed to create: {e}{RESET}")
                all_passed = False

    if not all_passed:
        raise ValidationError("Some required directories are missing")


def check_dependencies():
    """Check critical Python packages are installed."""
    required_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'redis',
        'pydantic',
        'jose',
        'cryptography',
        'sentry_sdk',
    ]

    all_passed = True
    for package in required_packages:
        try:
            __import__(package)
            print_check(f"Package: {package}", True)
        except ImportError:
            print_check(f"Package: {package}", False, "Not installed")
            all_passed = False

    if not all_passed:
        raise ValidationError("Missing required Python packages")


def check_security_headers():
    """Check security configuration."""
    checks = []

    # Check JWT secret strength
    jwt_secret = os.getenv('JWT_SECRET', '')
    checks.append((
        "JWT secret strength",
        len(jwt_secret) >= 32,
        f"Length: {len(jwt_secret)} chars"
    ))

    # Check CORS configuration
    cors = os.getenv('BACKEND_CORS_ORIGINS', '')
    has_localhost = 'localhost' in cors or '127.0.0.1' in cors
    checks.append((
        "CORS no localhost",
        not has_localhost,
        "localhost detected in CORS!" if has_localhost else "OK"
    ))

    # Check Frontend URL
    frontend_url = os.getenv('FRONTEND_URL', '')
    is_https = frontend_url.startswith('https://')
    checks.append((
        "Frontend URL uses HTTPS",
        is_https,
        frontend_url if frontend_url else "Not set"
    ))

    all_passed = True
    for name, passed, message in checks:
        print_check(name, passed, message)
        if not passed:
            all_passed = False

    if not all_passed:
        raise ValidationError("Security configuration issues detected")


def main():
    """Run all validation checks."""
    print(f"\n{BOLD}{GREEN}Production Readiness Validation{RESET}")
    print(f"{BOLD}Forex AI Platform{RESET}")

    checks = [
        ("Environment Configuration", check_environment),
        ("Required Environment Variables", check_required_env_vars),
        ("Optional Environment Variables", check_optional_env_vars),
        ("Security Configuration", check_security_headers),
        ("Python Dependencies", check_dependencies),
        ("Directory Structure", check_directories),
        ("Database Connectivity", check_database_connection),
        ("Redis Connectivity", check_redis_connection),
    ]

    failed_checks = []

    for check_name, check_func in checks:
        print_header(check_name)
        try:
            check_func()
        except ValidationError as e:
            failed_checks.append((check_name, str(e)))
        except Exception as e:
            failed_checks.append((check_name, f"Unexpected error: {e}"))

    # Print summary
    print_header("Validation Summary")

    if not failed_checks:
        print(f"\n{BOLD}{GREEN}✓ All checks passed!{RESET}")
        print(f"{GREEN}System is ready for production deployment.{RESET}\n")
        return 0
    else:
        print(f"\n{BOLD}{RED}✗ {len(failed_checks)} check(s) failed:{RESET}\n")
        for check_name, error in failed_checks:
            print(f"  {RED}•{RESET} {BOLD}{check_name}{RESET}")
            print(f"    {error}\n")

        print(f"{YELLOW}Please fix the issues above before deploying to production.{RESET}\n")
        return 1


if __name__ == "__main__":
    try:
        # Add parent directory to path to import app modules
        sys.path.insert(0, str(Path(__file__).parent.parent))
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Validation cancelled by user.{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Fatal error: {e}{RESET}")
        sys.exit(1)
