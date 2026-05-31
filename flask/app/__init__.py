from __future__ import annotations

from pathlib import Path

from flask import Flask

from app.config import Config
from app.extensions import csrf, db, login_manager, migrate


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        if not user_id.isdigit():
            return None
        return db.session.get(User, int(user_id))

    from app.blueprints.admin.routes import bp as admin_bp
    from app.blueprints.auth.routes import bp as auth_bp
    from app.blueprints.catalog.routes import bp as catalog_bp
    from app.blueprints.collection.routes import bp as collection_bp
    from app.blueprints.imports.routes import bp as imports_bp
    from app.blueprints.main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(collection_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(imports_bp)

    @app.context_processor
    def inject_globals() -> dict[str, object]:
        from app.models import VariantType

        return {"variant_types": [item.value for item in VariantType]}

    @app.cli.command("init-db")
    def init_db_command() -> None:
        from app.services.seed import seed_demo_data

        db.create_all()
        seed_demo_data()
        print("Database initialized with demo data.")

    return app
