from flask_caching import Cache
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect


db = SQLAlchemy()
cache = Cache()
mail = Mail()
babel = Babel()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
