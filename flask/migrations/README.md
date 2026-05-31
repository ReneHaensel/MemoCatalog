This directory is reserved for Flask-Migrate/Alembic revisions.

Create the migration environment with:

```bash
flask --app wsgi db init
flask --app wsgi db migrate -m "initial schema"
flask --app wsgi db upgrade
```
