from sqlalchemy import Column, Integer, String, Text, DateTime, func
from core.database import Base


class SystemConfig(Base):
    """Модель системных настроек."""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), nullable=False, unique=True)
    config_value = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now())
    
    __table_args__ = {'extend_existing': True}