"""Migration V2: refactor IA-first.

Cambios:
1. ALTER appraisals: agregar code, assigned_to, client_*, status nuevo, suggested_*, etc
2. CREATE market_listings, monthly_reports, inbox_messages, appraisal_comparables
3. Hace `final_value` nullable en appraisals

Idempotente: si una columna/tabla ya existe, salta.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pymysql
from core.config import settings


ALTERS_APPRAISALS = [
    "ALTER TABLE appraisals ADD COLUMN code VARCHAR(20) UNIQUE",
    "ALTER TABLE appraisals ADD COLUMN assigned_to INT",
    "ALTER TABLE appraisals ADD COLUMN client_name VARCHAR(200)",
    "ALTER TABLE appraisals ADD COLUMN client_contact VARCHAR(200)",
    "ALTER TABLE appraisals ADD COLUMN client_email VARCHAR(200)",
    "ALTER TABLE appraisals ADD COLUMN suggested_value_min FLOAT",
    "ALTER TABLE appraisals ADD COLUMN suggested_value_max FLOAT",
    "ALTER TABLE appraisals ADD COLUMN suggested_value_mode FLOAT",
    "ALTER TABLE appraisals ADD COLUMN suggested_value_per_m2 FLOAT",
    "ALTER TABLE appraisals ADD COLUMN confidence_score FLOAT",
    "ALTER TABLE appraisals ADD COLUMN cap_rate FLOAT",
    "ALTER TABLE appraisals ADD COLUMN rental_estimate FLOAT",
    "ALTER TABLE appraisals ADD COLUMN comparables_count INT DEFAULT 0",
    "ALTER TABLE appraisals ADD COLUMN method VARCHAR(40) DEFAULT 'hybrid'",
    "ALTER TABLE appraisals ADD COLUMN ai_summary TEXT",
    "ALTER TABLE appraisals ADD COLUMN ai_recommendations TEXT",
    "ALTER TABLE appraisals ADD COLUMN last_analyzed_at DATETIME",
    "ALTER TABLE appraisals MODIFY COLUMN final_value FLOAT NULL",
    "ALTER TABLE appraisals MODIFY COLUMN status VARCHAR(30) DEFAULT 'solicitada'",
]

CREATE_MARKET_LISTINGS = """
CREATE TABLE IF NOT EXISTS market_listings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(40) DEFAULT 'seed',
    source_url VARCHAR(500),
    external_id VARCHAR(80),
    title VARCHAR(200) NOT NULL,
    property_type VARCHAR(40) NOT NULL,
    operation VARCHAR(20) DEFAULT 'venta',
    province VARCHAR(80),
    city VARCHAR(120),
    neighborhood VARCHAR(120),
    address VARCHAR(250),
    latitude FLOAT,
    longitude FLOAT,
    total_area_m2 FLOAT,
    covered_area_m2 FLOAT,
    rooms INT,
    bedrooms INT,
    bathrooms INT,
    age_years INT,
    `condition` VARCHAR(40),
    orientation VARCHAR(20),
    floor INT,
    parking_spots INT,
    price FLOAT NOT NULL,
    currency VARCHAR(5) DEFAULT 'USD',
    price_per_m2 FLOAT,
    status VARCHAR(20) DEFAULT 'active',
    days_on_market INT DEFAULT 0,
    description TEXT,
    photos_count INT DEFAULT 0,
    raw_data TEXT,
    captured_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX ix_listing_source (source),
    INDEX ix_listing_type (property_type),
    INDEX ix_listing_city (city),
    INDEX ix_listing_neighborhood (neighborhood),
    INDEX ix_listing_status (status),
    INDEX ix_listing_city_type (city, property_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

CREATE_MONTHLY_REPORTS = """
CREATE TABLE IF NOT EXISTS monthly_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    period_year INT NOT NULL,
    period_month INT NOT NULL,
    region VARCHAR(80) DEFAULT 'CABA',
    kind VARCHAR(20) DEFAULT 'mensual',
    tasar_index FLOAT,
    median_price_per_m2 FLOAT,
    yoy_change_pct FLOAT,
    mom_change_pct FLOAT,
    active_listings INT,
    avg_days_on_market INT,
    new_permits INT,
    top_zones TEXT,
    pdf_url VARCHAR(500),
    pages_count INT DEFAULT 0,
    published_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_report_region (region),
    UNIQUE KEY uq_monthly_period_region (period_year, period_month, region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

CREATE_INBOX = """
CREATE TABLE IF NOT EXISTS inbox_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    workspace_id INT NOT NULL,
    user_id INT,
    kind VARCHAR(40) NOT NULL,
    sender_type VARCHAR(40) DEFAULT 'user',
    sender_name VARCHAR(200),
    sender_subtitle VARCHAR(200),
    avatar_color VARCHAR(20),
    subject VARCHAR(250) NOT NULL,
    preview VARCHAR(500),
    body TEXT,
    related_appraisal_id INT,
    related_property_id INT,
    related_url VARCHAR(500),
    is_read TINYINT(1) DEFAULT 0,
    is_assigned_to_me TINYINT(1) DEFAULT 0,
    priority VARCHAR(20) DEFAULT 'normal',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME,
    scheduled_for DATETIME,
    actions TEXT,
    INDEX ix_inbox_ws (workspace_id),
    INDEX ix_inbox_user (user_id),
    INDEX ix_inbox_kind (kind),
    INDEX ix_inbox_read (is_read),
    INDEX ix_inbox_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

CREATE_APPRAISAL_COMPARABLES = """
CREATE TABLE IF NOT EXISTS appraisal_comparables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    appraisal_id INT NOT NULL,
    market_listing_id INT NOT NULL,
    match_score FLOAT,
    distance_m INT,
    weight FLOAT DEFAULT 1.0,
    adjusted_price FLOAT,
    adjusted_price_per_m2 FLOAT,
    adjustments_json TEXT,
    status VARCHAR(20) DEFAULT 'included',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_apcomp_appraisal (appraisal_id),
    INDEX ix_apcomp_listing (market_listing_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def main():
    conn = pymysql.connect(
        host=settings.DB_HOST, port=settings.DB_PORT,
        user=settings.DB_USER, password=settings.DB_PASSWORD,
        database=settings.DB_NAME, ssl={"fake_flag_to_enable_tls": True},
    )
    try:
        with conn.cursor() as cur:
            print("== ALTER appraisals ==")
            for sql in ALTERS_APPRAISALS:
                try:
                    cur.execute(sql)
                    print(f"  OK: {sql[:90]}")
                except pymysql.err.OperationalError as e:
                    if any(x in str(e) for x in ["Duplicate column", "1060", "1054"]):
                        print(f"  SKIP: {sql[:90]}")
                    else:
                        print(f"  FAIL: {sql[:90]} -- {e}")
            print("\n== CREATE market_listings ==")
            cur.execute(CREATE_MARKET_LISTINGS); print("  OK")
            print("== CREATE monthly_reports ==")
            cur.execute(CREATE_MONTHLY_REPORTS); print("  OK")
            print("== CREATE inbox_messages ==")
            cur.execute(CREATE_INBOX); print("  OK")
            print("== CREATE appraisal_comparables ==")
            cur.execute(CREATE_APPRAISAL_COMPARABLES); print("  OK")
        conn.commit()
        print("\nMigration V2 OK")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
