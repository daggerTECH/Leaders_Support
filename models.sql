-- -----------------------------------------------------
-- Database: leaders_ticketing
-- -----------------------------------------------------

CREATE DATABASE IF NOT EXISTS leaders_data
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE leaders_data;

-- -----------------------------------------------------
-- USERS TABLE
-- -----------------------------------------------------
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INT NOT NULL AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin','agent') NOT NULL DEFAULT 'agent',
    is_verified TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -----------------------------------------------------
-- TICKETS TABLE (AGENT + SLA + SLACK READY)
-- -----------------------------------------------------
DROP TABLE IF EXISTS tickets;

CREATE TABLE tickets (
    id INT NOT NULL AUTO_INCREMENT,

    ticket_code VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,

    status ENUM('Open','In Progress','Resolved') DEFAULT 'Open',
    priority ENUM('High','Medium','Low') DEFAULT 'Medium',

    -- 👤 Assigned Agent
    assigned_to INT NULL,

    -- ⏱ SLA HOURS (High=24, Medium=48, Low=72)
    sla_hours INT NOT NULL DEFAULT 72,

    -- 🔔 Slack notification flag
    slack_notified TINYINT(1) NOT NULL DEFAULT 0,

    -- 🔐 Email deduplication
    message_id VARCHAR(255) UNIQUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    CONSTRAINT fk_ticket_assigned_agent
        FOREIGN KEY (assigned_to)
        REFERENCES users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -----------------------------------------------------
-- NOTIFICATIONS TABLE (IN-APP)
-- -----------------------------------------------------
DROP TABLE IF EXISTS notifications;

CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    ticket_id INT NOT NULL,
    ticket_code VARCHAR(50) NOT NULL,
    message VARCHAR(255) NOT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -----------------------------------------------------
-- OPTIONAL: SAMPLE VERIFIED ADMIN USER
-- -----------------------------------------------------
-- Generate hash in Python:
-- from werkzeug.security import generate_password_hash
-- print(generate_password_hash("admin123"))
--
-- INSERT INTO users (email, password, role, is_verified)
-- VALUES ('admin@leaders.st', '<HASH>', 'admin', 1);
