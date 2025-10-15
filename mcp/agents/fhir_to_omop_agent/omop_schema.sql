-- Minimal OMOP subset for demo (PostgreSQL)
CREATE TABLE IF NOT EXISTS person (
  person_id INTEGER PRIMARY KEY,
  gender_concept_id INTEGER,
  year_of_birth INTEGER,
  month_of_birth INTEGER,
  day_of_birth INTEGER
);

CREATE TABLE IF NOT EXISTS measurement (
  measurement_id INTEGER PRIMARY KEY,
  person_id INTEGER REFERENCES person(person_id),
  measurement_concept_id INTEGER,
  measurement_date DATE,
  measurement_datetime TIMESTAMP,
  value_as_number DOUBLE PRECISION,
  unit_concept_id INTEGER
);

CREATE TABLE IF NOT EXISTS condition_occurrence (
  condition_occurrence_id INTEGER PRIMARY KEY,
  person_id INTEGER REFERENCES person(person_id),
  condition_concept_id INTEGER,
  condition_start_date DATE,
  condition_start_datetime TIMESTAMP
);
