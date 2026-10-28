CREATE TABLE IF NOT EXISTS countries (
    iso CHAR(3) PRIMARY KEY,
    name VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    name VARCHAR(256) PRIMARY KEY,
    country CHAR(3) NOT NULL REFERENCES countries(iso)
);

CREATE TABLE IF NOT EXISTS riders (
    bib_num INT PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    dob DATE NOT NULL CHECK (dob < CURRENT_DATE),
    team VARCHAR(256) NOT NULL REFERENCES teams(name) ON UPDATE CASCADE,
    country CHAR(3) NOT NULL REFERENCES countries(iso) -- country of the rider, not the team
);

CREATE TABLE IF NOT EXISTS locations (
    name VARCHAR(256) PRIMARY KEY,
    country CHAR(3) NOT NULL REFERENCES countries(iso)
);

CREATE TABLE IF NOT EXISTS stages (
    id VARCHAR(64) PRIMARY KEY,
    date DATE NOT NULL,
    start_location VARCHAR(256) NOT NULL REFERENCES locations(name) ON UPDATE CASCADE,
    end_location VARCHAR(256) NOT NULL REFERENCES locations(name) ON UPDATE CASCADE,
    dist_covered DECIMAL(10, 2) NOT NULL CHECK (dist_covered > 0),
    type VARCHAR(64) NOT NULL CHECK (type IN ('flat', 'hilly', 'mountain', 'individual time-trial'))
);

-- adjusted time is derived attribute
CREATE TABLE IF NOT EXISTS stage_results (
    rider_bib INT REFERENCES riders(bib_num),
    stage_id VARCHAR(64) REFERENCES stages(id),
    rank INT NOT NULL CHECK (rank >= 1),
    finish_time DECIMAL(10, 2) NOT NULL CHECK (finish_time >= 0),
    time_bonus DECIMAL(10, 2) NOT NULL CHECK (time_bonus >= 0),
    time_penalty DECIMAL(10, 2) NOT NULL CHECK (time_penalty >= 0),
    PRIMARY KEY (rider_bib, stage_id),
    UNIQUE (stage_id, rank)
);

CREATE TABLE IF NOT EXISTS rider_exits (
    rider_bib INT PRIMARY KEY REFERENCES riders(bib_num),
    stage_id VARCHAR(64) NOT NULL REFERENCES stages(id),
    reason VARCHAR(256) NOT NULL
);

CREATE TABLE IF NOT EXISTS awards (
    name VARCHAR(64) PRIMARY KEY CHECK (name IN (
        'general',
        'points',
        'king of the mountains',
        'young rider',
        'best team'
    ))
);

CREATE TABLE IF NOT EXISTS team_awards (
    award VARCHAR(64) PRIMARY KEY REFERENCES awards(name) ON UPDATE CASCADE,
    team VARCHAR(256) NOT NULL REFERENCES teams(name) ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS rider_awards (
    award VARCHAR(64) PRIMARY KEY REFERENCES awards(name) ON UPDATE CASCADE,
    rider_bib INT NOT NULL REFERENCES riders(bib_num)
);