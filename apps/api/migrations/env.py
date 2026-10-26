from alembic import context
from sqlalchemy import create_engine

from cinebase_api.models import Base
from cinebase_api.settings import get_settings

config = context.config


def run_migrations_online() -> None:
    # An explicit URL (tests, CLI) wins over the environment.
    url = config.attributes.get("database_url") or get_settings().database_url
    connectable = config.attributes.get("connection") or create_engine(url)
    if hasattr(connectable, "connect"):
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=Base.metadata)
            with context.begin_transaction():
                context.run_migrations()
    else:
        context.configure(connection=connectable, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
