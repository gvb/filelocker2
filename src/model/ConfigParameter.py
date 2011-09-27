# -*- coding: utf-8 -*-
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import Column,String,Enum
class ConfigParameter(Base):
    __tablename__ = "config"
    config_parameter_name = Column(String(30), primary_key=True)
    config_parameter_description = Column(String)
    config_parameter_type = Column(Enum("boolean", "number", "text", "datetime"))
    config_parameter_value = Column(String)

    def __init__ (self, parameterName, parameterDescription, pType, value):
        self.config_parameter_name = parameterName
        self.config_parameter_description = parameterDescription
        self.config_parameter_type = pType
        self.config_parameter_value = value