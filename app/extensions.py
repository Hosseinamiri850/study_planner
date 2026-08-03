"""Flask extensions shared across the application."""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
# Rate limiter. Storage backend is chosen at init time in create_app:
# Redis when REDIS_URL is set (production), in-memory otherwise (dev/test).
limiter = Limiter(key_func=get_remote_address)
