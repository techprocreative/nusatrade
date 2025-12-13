"""Custom SQLAlchemy types for cross-database compatibility."""

import uuid
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    
    Uses PostgreSQL's UUID type in production, stores as CHAR(32) in SQLite.
    This allows tests to run with SQLite while production uses PostgreSQL.
    
    Usage:
        id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Load the appropriate type for the database dialect."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        """Convert UUID to database-appropriate format on insert/update."""
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
        else:
            # For SQLite, store as hex string without dashes
            if isinstance(value, uuid.UUID):
                return value.hex
            elif isinstance(value, str):
                # Remove dashes if present
                return value.replace('-', '')
            return value

    def process_result_value(self, value, dialect):
        """Convert database value back to UUID on read."""
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            try:
                return uuid.UUID(value) if isinstance(value, str) else value
            except (ValueError, AttributeError):
                return value
        return value
