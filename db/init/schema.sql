CREATE TABLE rooms (
    room_id         VARCHAR(255) PRIMARY KEY,  -- natural key
    activated       BOOLEAN NOT NULL DEFAULT FALSE,
    webhook_url     VARCHAR(255) NOT NULL,
    token           VARCHAR(255) NOT NULL
);

CREATE TABLE users (
    room_id         VARCHAR(255) NOT NULL REFERENCES rooms (room_id) ON DELETE CASCADE,
    user_id         VARCHAR(255) NOT NULL,
    atcoder_id      VARCHAR(255) NOT NULL,
    PRIMARY KEY (room_id, user_id)  -- natural key
);

CREATE TABLE problems (
    problem_url     VARCHAR(255) NOT NULL PRIMARY KEY,  -- natural key
    problem_name    VARCHAR(255) NOT NULL
);

CREATE TABLE submissions (
    submission_url  VARCHAR(255) NOT NULL PRIMARY KEY,  -- natural key
    problem_url     VARCHAR(255) NOT NULL REFERENCES problems (problem_url),
    user_id         VARCHAR(255) NOT NULL,
    result          VARCHAR(255) NOT NULL,
    score           REAL NULL,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE last_reported (
    room_id         VARCHAR(255) NOT NULL REFERENCES rooms (room_id) ON DELETE CASCADE,
    last_reported   TIMESTAMP WITH TIME ZONE
);
