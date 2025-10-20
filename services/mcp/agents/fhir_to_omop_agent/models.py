from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy import Integer, String, Date, DateTime, Float, ForeignKey

Base = declarative_base()

class Person(Base):
    __tablename__ = "person"
    person_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gender_concept_id: Mapped[int | None] = mapped_column(Integer)
    year_of_birth: Mapped[int | None] = mapped_column(Integer)
    month_of_birth: Mapped[int | None] = mapped_column(Integer)
    day_of_birth: Mapped[int | None] = mapped_column(Integer)

class Measurement(Base):
    __tablename__ = "measurement"
    measurement_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("person.person_id"), index=True)
    measurement_concept_id: Mapped[int | None] = mapped_column(Integer)
    measurement_date: Mapped[Date | None] = mapped_column(Date)
    measurement_datetime: Mapped[DateTime | None] = mapped_column(DateTime)
    value_as_number: Mapped[float | None] = mapped_column(Float)
    unit_concept_id: Mapped[int | None] = mapped_column(Integer)

class ConditionOccurrence(Base):
    __tablename__ = "condition_occurrence"
    condition_occurrence_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("person.person_id"), index=True)
    condition_concept_id: Mapped[int | None] = mapped_column(Integer)
    condition_start_date: Mapped[Date | None] = mapped_column(Date)
    condition_start_datetime: Mapped[DateTime | None] = mapped_column(DateTime)
