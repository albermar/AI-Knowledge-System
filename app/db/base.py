from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

#goal: This code defines a base class for SQLAlchemy models using the Declarative system. By inheriting from this Base class, you can create your own database models that will be mapped to database tables. The Base class serves as a common ancestor for all your models, allowing you to easily manage and organize your database schema.