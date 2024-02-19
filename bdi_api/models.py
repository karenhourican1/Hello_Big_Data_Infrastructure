from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Numeric
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Aircraft(Base):
    __tablename__ = 'aircraft'

    aircraft_id = Column(Integer, primary_key=True)
    icao = Column(String(50), unique=True, nullable=False)
    registration = Column(String(50))
    type = Column(String(50))


class Position(Base):
    __tablename__ = 'positions'

    position_id = Column(Integer, primary_key=True)
    aircraft_id = Column(Integer, ForeignKey('aircraft.aircraft_id'), nullable=False)
    timestamp = Column(Numeric)
    latitude = Column(Float)
    longitude = Column(Float)


class Statistic(Base):
    __tablename__ = 'statistics'

    statistics_id = Column(Integer, primary_key=True)
    aircraft_id = Column(Integer, ForeignKey('aircraft.aircraft_id'), nullable=False)
    max_altitude_baro = Column(Integer)
    max_ground_speed = Column(Float)
    had_emergency = Column(Boolean)
