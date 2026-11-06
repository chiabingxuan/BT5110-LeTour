-- Task 4 star schema: one fact table of stage results and its dimensions, in its own schema "star"
-- so it never interferes with the normalised tables the dashboard reads.
-- Dimensions are deliberately denormalised (country names copied into team, rider and stage rows),
-- and the fact table stores the derived adjusted_time, to save joins at query time.

CREATE SCHEMA IF NOT EXISTS star;

DROP TABLE IF EXISTS star.fact_results;
DROP TABLE IF EXISTS star.dim_rider;
DROP TABLE IF EXISTS star.dim_team;
DROP TABLE IF EXISTS star.dim_stage;
DROP TABLE IF EXISTS star.dim_country;
DROP TABLE IF EXISTS star.dim_date;

CREATE TABLE star.dim_country (
    country_key SERIAL PRIMARY KEY,
    iso CHAR(3) NOT NULL UNIQUE,
    country_name VARCHAR(64) NOT NULL
);

CREATE TABLE star.dim_team (
    team_key SERIAL PRIMARY KEY,
    team_name VARCHAR(256) NOT NULL UNIQUE,
    team_country_iso CHAR(3) NOT NULL,
    team_country_name VARCHAR(64) NOT NULL
);

CREATE TABLE star.dim_rider (
    rider_key SERIAL PRIMARY KEY,
    bib_num INT NOT NULL UNIQUE,
    rider_name VARCHAR(256) NOT NULL,
    dob DATE NOT NULL,
    age_at_start INT NOT NULL,
    nationality_iso CHAR(3) NOT NULL,
    nationality_name VARCHAR(64) NOT NULL,
    team_name VARCHAR(256) NOT NULL,
    team_country_iso CHAR(3) NOT NULL,
    status VARCHAR(16) NOT NULL,
    exit_stage_no INT,
    exit_reason VARCHAR(256)
);

CREATE TABLE star.dim_stage (
    stage_key SERIAL PRIMARY KEY,
    stage_id VARCHAR(64) NOT NULL UNIQUE,
    stage_no INT NOT NULL UNIQUE,
    stage_date DATE NOT NULL,
    stage_type VARCHAR(64) NOT NULL,
    type_label VARCHAR(16) NOT NULL,
    start_location VARCHAR(256) NOT NULL,
    start_country_iso CHAR(3) NOT NULL,
    start_country_name VARCHAR(64) NOT NULL,
    end_location VARCHAR(256) NOT NULL,
    end_country_iso CHAR(3) NOT NULL,
    end_country_name VARCHAR(64) NOT NULL,
    dist_km NUMERIC(10, 2) NOT NULL
);

CREATE TABLE star.dim_date (
    date_key INT PRIMARY KEY,           -- yyyymmdd
    full_date DATE NOT NULL UNIQUE,
    day_of_week VARCHAR(9) NOT NULL,
    race_day INT NOT NULL,              -- 1 = first stage day
    is_weekend BOOLEAN NOT NULL
);

-- Grain: one row per rider per stage completed.
CREATE TABLE star.fact_results (
    rider_key INT NOT NULL REFERENCES star.dim_rider(rider_key),
    stage_key INT NOT NULL REFERENCES star.dim_stage(stage_key),
    team_key INT NOT NULL REFERENCES star.dim_team(team_key),
    nationality_key INT NOT NULL REFERENCES star.dim_country(country_key),
    date_key INT NOT NULL REFERENCES star.dim_date(date_key),
    stage_rank INT NOT NULL,
    finish_time NUMERIC(10, 2) NOT NULL,
    time_bonus NUMERIC(10, 2) NOT NULL,
    time_penalty NUMERIC(10, 2) NOT NULL,
    adjusted_time NUMERIC(10, 2) NOT NULL,   -- stored: finish_time - time_bonus + time_penalty
    PRIMARY KEY (rider_key, stage_key)
);

CREATE INDEX ON star.fact_results (stage_key);
CREATE INDEX ON star.fact_results (team_key);
