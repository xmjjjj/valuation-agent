-- Patent valuation database schema (MySQL 8.0)

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS patents (
    patent_id       VARCHAR(20) PRIMARY KEY,
    title           TEXT NOT NULL,
    abstract        TEXT,
    claims          MEDIUMTEXT,
    description     MEDIUMTEXT,
    applicant       VARCHAR(200),
    inventor        VARCHAR(200),
    application_no  VARCHAR(32),
    ipc_code        VARCHAR(20),
    grant_year      INT,
    legal_status    VARCHAR(20) COMMENT '有效/失效/转让/许可',
    citation_count  INT DEFAULT 0,
    has_award       TINYINT(1) DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_patents_ipc (ipc_code),
    INDEX idx_patents_grant_year (grant_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS patent_citations (
    patent_id       VARCHAR(20) NOT NULL,
    cited_patent_id VARCHAR(20) NOT NULL,
    PRIMARY KEY (patent_id, cited_patent_id),
    CONSTRAINT fk_citations_patent
        FOREIGN KEY (patent_id) REFERENCES patents(patent_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS industry_data (
    ipc_prefix          VARCHAR(10) PRIMARY KEY,
    market_size         DECIMAL(20, 2) NOT NULL COMMENT '市场规模（亿元）',
    growth_rate         DECIMAL(5, 2) NOT NULL COMMENT '增长率（%）',
    competition_level   VARCHAR(20) NOT NULL COMMENT '低/中/高',
    policy_support      INT DEFAULT 0 COMMENT '0-100',
    max_market_value    DECIMAL(20, 2) COMMENT '行业估值上限（万元）',
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ipc_frontier (
    ipc_code        VARCHAR(20) PRIMARY KEY,
    is_frontier     TINYINT(1) DEFAULT 1,
    note            VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ipc_citation_stats (
    ipc_prefix      VARCHAR(10) NOT NULL,
    grant_year      INT NOT NULL,
    avg_citation    DECIMAL(10, 2) NOT NULL DEFAULT 1,
    sample_size     INT DEFAULT 0,
    PRIMARY KEY (ipc_prefix, grant_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS valuation_runs (
    run_id              CHAR(36) PRIMARY KEY,
    patent_id           VARCHAR(20) NOT NULL,
    innovation_score    DECIMAL(5, 2),
    innovation_level    VARCHAR(20),
    key_innovations     JSON,
    scene_labels        JSON,
    scene_score         DECIMAL(5, 2),
    market_score        DECIMAL(5, 2),
    risk_index          DECIMAL(5, 2),
    final_score         DECIMAL(5, 2),
    valuation_wan       DECIMAL(20, 2) COMMENT '估值（万元）',
    pledge_amount_wan   DECIMAL(20, 2) COMMENT '质押额度（万元）',
    report_json         JSON,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_runs_patent
        FOREIGN KEY (patent_id) REFERENCES patents(patent_id) ON DELETE CASCADE,
    INDEX idx_runs_patent (patent_id),
    INDEX idx_runs_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
