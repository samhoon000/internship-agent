# Database Migration Workflow

This project uses **Alembic** to manage database schema migrations. Schema changes must not be executed dynamically on startup. Instead, use the workflow described below.

## Running Existing Migrations
When starting the application in a new environment, apply the migration history to sync the database schema:

```bash
cd python_scraper
python -m alembic upgrade head
```

## Generating a New Migration
When modifying model definitions in `python_scraper/database/models.py`:

1. Define the changes in `models.py`.
2. Generate the migration file using `alembic revision --autogenerate`:

```bash
cd python_scraper
python -m alembic revision --autogenerate -m "describe_the_change"
```

3. Review the generated script in `python_scraper/alembic/versions/`. Ensure DDL commands match expectations and incorporate conditional checks where necessary (to support running against databases where columns/tables might already have been partially initialized).

## Rollback a Migration
To rollback the last migration:

```bash
cd python_scraper
python -m alembic downgrade -1
```

To rollback all migrations:

```bash
cd python_scraper
python -m alembic downgrade base
```
