from sqlalchemy import Column, Integer, String, func, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import DateTime

Base = declarative_base()


class Brand(Base):
    __tablename__ = 'brands'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    brand_id = Column(Integer)

    models = relationship('Model', back_populates='brand')


class Model(Base):
    __tablename__ = 'models'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    model_id = Column(Integer)
    brand_id = Column(Integer, ForeignKey('brands.id'))

    brand = relationship('Brand', back_populates='models')
    cars = relationship('Car', back_populates='model')
    current = relationship('CurrentModel', back_populates='model')


class Car(Base):
    __tablename__ = "cars"
    id = Column(Integer, primary_key=True)
    car_id = Column(Integer, unique=True)
    name = Column(String(100), nullable=False)
    price = Column(Integer, nullable=False)
    mileage = Column(Integer, nullable=False)
    location = Column(String(100))
    car_url = Column(String(300), nullable=False)
    car_images = Column(String(1000), nullable=True)
    auction_url = Column(String(300), nullable=True)
    auction_images = Column(String(1500), nullable=True)
    created = Column(DateTime, default=func.now())
    updated = Column(DateTime, default=func.now(), onupdate=func.now())

    model_id = Column(Integer, ForeignKey('models.id'))
    model = relationship('Model', back_populates='cars')


class CurrentModel(Base):
    __tablename__ = "current"
    id = Column(Integer, primary_key=True)

    model_id = Column(Integer, ForeignKey('models.id'), nullable=True)
    model = relationship('Model', back_populates='current')
