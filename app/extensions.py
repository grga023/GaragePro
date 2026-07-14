"""Shared Flask extensions (single instances, initialised in the app factory)."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_babel import Babel, lazy_gettext as _l

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
babel = Babel()
login_manager.login_view = "auth.login"
login_manager.login_message = _l("Molimo prijavite se da biste pristupili ovoj stranici.")
login_manager.login_message_category = "warning"
