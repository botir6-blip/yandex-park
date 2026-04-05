BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'language_code') THEN
        CREATE TYPE language_code AS ENUM ('uz_cyrl', 'uz_latn', 'ru');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'driver_status') THEN
        CREATE TYPE driver_status AS ENUM ('active', 'inactive', 'blocked');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'card_status') THEN
        CREATE TYPE card_status AS ENUM ('active', 'inactive', 'blocked', 'deleted');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'withdrawal_status') THEN
        CREATE TYPE withdrawal_status AS ENUM ('new', 'accepted', 'paid', 'rejected', 'cancelled');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deposit_status') THEN
        CREATE TYPE deposit_status AS ENUM ('new', 'processing', 'credited', 'rejected', 'cancelled');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transaction_type') THEN
        CREATE TYPE transaction_type AS ENUM (
            'balance_topup',
            'balance_adjustment_plus',
            'balance_adjustment_minus',
            'bonus_plus',
            'bonus_minus',
            'withdrawal_hold',
            'withdrawal_paid',
            'withdrawal_rejected',
            'withdrawal_cancelled',
            'deposit_created',
            'deposit_credited',
            'deposit_rejected',
            'reserve_changed'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'admin_role') THEN
        CREATE TYPE admin_role AS ENUM ('super_admin', 'operator', 'viewer');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'admin_status') THEN
        CREATE TYPE admin_status AS ENUM ('active', 'inactive', 'blocked');
    END IF;
END
$$;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS drivers (
    id                  BIGSERIAL PRIMARY KEY,
    full_name           VARCHAR(150) NOT NULL,
    phone               VARCHAR(20) NOT NULL,
    telegram_id         BIGINT UNIQUE,
    telegram_username   VARCHAR(100),
    park_driver_id      VARCHAR(100),
    yandex_contractor_profile_id VARCHAR(100),
    language            language_code NOT NULL DEFAULT 'ru',
    status              driver_status NOT NULL DEFAULT 'active',
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE,
    bound_at            TIMESTAMP NULL,
    last_seen_at        TIMESTAMP NULL,
    note                TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_drivers_phone UNIQUE (phone),
    CONSTRAINT uq_drivers_park_driver_id UNIQUE (park_driver_id),
    CONSTRAINT uq_drivers_yandex_contractor_profile_id UNIQUE (yandex_contractor_profile_id)
);

DROP TRIGGER IF EXISTS trg_drivers_updated_at ON drivers;
CREATE TRIGGER trg_drivers_updated_at
BEFORE UPDATE ON drivers
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_drivers_status ON drivers(status);
CREATE INDEX IF NOT EXISTS idx_drivers_full_name ON drivers(full_name);
CREATE INDEX IF NOT EXISTS idx_drivers_telegram_id ON drivers(telegram_id);
CREATE INDEX IF NOT EXISTS idx_drivers_yandex_contractor_profile_id ON drivers(yandex_contractor_profile_id);

CREATE TABLE IF NOT EXISTS driver_wallets (
    id                      BIGSERIAL PRIMARY KEY,
    driver_id               BIGINT NOT NULL UNIQUE REFERENCES drivers(id) ON DELETE CASCADE,
    main_balance            NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (main_balance >= 0),
    bonus_balance           NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (bonus_balance >= 0),
    min_reserve_balance     NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (min_reserve_balance >= 0),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_driver_wallets_updated_at ON driver_wallets;
CREATE TRIGGER trg_driver_wallets_updated_at
BEFORE UPDATE ON driver_wallets
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS driver_cards (
    id                      BIGSERIAL PRIMARY KEY,
    driver_id               BIGINT NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    card_number_encrypted   TEXT NOT NULL,
    card_mask               VARCHAR(25) NOT NULL,
    holder_name             VARCHAR(150),
    bank_name               VARCHAR(100),
    card_type               VARCHAR(20),
    is_primary              BOOLEAN NOT NULL DEFAULT FALSE,
    status                  card_status NOT NULL DEFAULT 'active',
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_card_mask_not_empty CHECK (length(card_mask) >= 8)
);

DROP TRIGGER IF EXISTS trg_driver_cards_updated_at ON driver_cards;
CREATE TRIGGER trg_driver_cards_updated_at
BEFORE UPDATE ON driver_cards
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_driver_cards_driver_id ON driver_cards(driver_id);
CREATE INDEX IF NOT EXISTS idx_driver_cards_status ON driver_cards(status);

CREATE UNIQUE INDEX IF NOT EXISTS uq_driver_cards_one_primary_active
ON driver_cards(driver_id)
WHERE is_primary = TRUE AND status = 'active';

CREATE TABLE IF NOT EXISTS admins (
    id                  BIGSERIAL PRIMARY KEY,
    full_name           VARCHAR(150) NOT NULL,
    login               VARCHAR(100) NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,
    role                admin_role NOT NULL DEFAULT 'operator',
    status              admin_status NOT NULL DEFAULT 'active',
    telegram_id         BIGINT UNIQUE,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_admins_updated_at ON admins;
CREATE TRIGGER trg_admins_updated_at
BEFORE UPDATE ON admins
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_admins_role ON admins(role);
CREATE INDEX IF NOT EXISTS idx_admins_status ON admins(status);

CREATE TABLE IF NOT EXISTS settings (
    id              BIGSERIAL PRIMARY KEY,
    key             VARCHAR(100) NOT NULL UNIQUE,
    value           TEXT NOT NULL,
    description     TEXT,
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_settings_updated_at ON settings;
CREATE TRIGGER trg_settings_updated_at
BEFORE UPDATE ON settings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

INSERT INTO settings (key, value, description)
VALUES
    ('deposit_commission_percent', '1.00', 'Пополнение комиссияси, фоизда'),
    ('global_min_reserve_balance', '20000.00', 'Умумий минимал қолдиқ'),
    ('min_withdraw_amount', '1000.00', 'Минимал пул ечиш суммаси'),
    ('max_withdraw_amount', '10000000.00', 'Максимал пул ечиш суммаси'),
    ('support_contact', '@support', 'Оператор контакти'),
    ('default_language', 'ru', 'Янги ҳайдовчи учун стандарт тил')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS deposit_requests (
    id                      BIGSERIAL PRIMARY KEY,
    driver_id               BIGINT NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    requested_amount        NUMERIC(14,2) NOT NULL CHECK (requested_amount > 0),
    commission_percent      NUMERIC(5,2) NOT NULL DEFAULT 1.00 CHECK (commission_percent >= 0),
    commission_amount       NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (commission_amount >= 0),
    credited_amount         NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (credited_amount >= 0),
    status                  deposit_status NOT NULL DEFAULT 'new',
    payment_method          VARCHAR(50),
    note                    TEXT,
    external_payment_id     VARCHAR(150),
    processed_by_admin_id   BIGINT REFERENCES admins(id) ON DELETE SET NULL,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at            TIMESTAMP NULL,
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_deposit_requests_updated_at ON deposit_requests;
CREATE TRIGGER trg_deposit_requests_updated_at
BEFORE UPDATE ON deposit_requests
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_deposit_requests_driver_id ON deposit_requests(driver_id);
CREATE INDEX IF NOT EXISTS idx_deposit_requests_status ON deposit_requests(status);
CREATE INDEX IF NOT EXISTS idx_deposit_requests_created_at ON deposit_requests(created_at DESC);

CREATE TABLE IF NOT EXISTS withdrawal_requests (
    id                      BIGSERIAL PRIMARY KEY,
    request_no              UUID NOT NULL DEFAULT gen_random_uuid(),
    driver_id               BIGINT NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    card_id                 BIGINT NOT NULL REFERENCES driver_cards(id) ON DELETE RESTRICT,
    requested_amount        NUMERIC(14,2) NOT NULL CHECK (requested_amount > 0),
    commission_percent      NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (commission_percent >= 0),
    commission_amount       NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (commission_amount >= 0),
    payout_amount           NUMERIC(14,2) NOT NULL CHECK (payout_amount >= 0),
    status                  withdrawal_status NOT NULL DEFAULT 'new',
    driver_comment          TEXT,
    admin_note              TEXT,
    external_payout_id      VARCHAR(150),
    processed_by_admin_id   BIGINT REFERENCES admins(id) ON DELETE SET NULL,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    accepted_at             TIMESTAMP NULL,
    paid_at                 TIMESTAMP NULL,
    rejected_at             TIMESTAMP NULL,
    cancelled_at            TIMESTAMP NULL,
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_withdrawal_request_no UNIQUE (request_no)
);

DROP TRIGGER IF EXISTS trg_withdrawal_requests_updated_at ON withdrawal_requests;
CREATE TRIGGER trg_withdrawal_requests_updated_at
BEFORE UPDATE ON withdrawal_requests
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_driver_id ON withdrawal_requests(driver_id);
CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_card_id ON withdrawal_requests(card_id);
CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_status ON withdrawal_requests(status);
CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_created_at ON withdrawal_requests(created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_withdrawal_one_open_per_driver
ON withdrawal_requests(driver_id)
WHERE status IN ('new', 'accepted');

CREATE TABLE IF NOT EXISTS transactions (
    id                          BIGSERIAL PRIMARY KEY,
    driver_id                   BIGINT NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    type                        transaction_type NOT NULL,
    amount                      NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
    main_balance_before         NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (main_balance_before >= 0),
    main_balance_after          NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (main_balance_after >= 0),
    bonus_balance_before        NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (bonus_balance_before >= 0),
    bonus_balance_after         NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (bonus_balance_after >= 0),
    reserve_balance_before      NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (reserve_balance_before >= 0),
    reserve_balance_after       NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (reserve_balance_after >= 0),
    comment                     TEXT,
    related_withdrawal_id       BIGINT REFERENCES withdrawal_requests(id) ON DELETE SET NULL,
    related_deposit_id          BIGINT REFERENCES deposit_requests(id) ON DELETE SET NULL,
    created_by_admin_id         BIGINT REFERENCES admins(id) ON DELETE SET NULL,
    created_at                  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_driver_id ON transactions(driver_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
    id                  BIGSERIAL PRIMARY KEY,
    admin_id            BIGINT REFERENCES admins(id) ON DELETE SET NULL,
    actor_type          VARCHAR(20) NOT NULL DEFAULT 'admin',
    action              VARCHAR(100) NOT NULL,
    entity_type         VARCHAR(50) NOT NULL,
    entity_id           BIGINT,
    details             JSONB,
    ip_address          VARCHAR(64),
    created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_admin_id ON audit_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);

CREATE OR REPLACE VIEW v_driver_finance AS
SELECT
    d.id AS driver_id,
    d.full_name,
    d.phone,
    d.telegram_id,
    d.language,
    d.status,
    COALESCE(w.main_balance, 0) AS main_balance,
    COALESCE(w.bonus_balance, 0) AS bonus_balance,
    COALESCE(w.min_reserve_balance, 0) AS min_reserve_balance,
    GREATEST(COALESCE(w.main_balance, 0) - COALESCE(w.min_reserve_balance, 0), 0) AS available_to_withdraw
FROM drivers d
LEFT JOIN driver_wallets w ON w.driver_id = d.id;

CREATE OR REPLACE FUNCTION create_wallet_for_driver()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO driver_wallets (driver_id)
    VALUES (NEW.id)
    ON CONFLICT (driver_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_create_wallet_for_driver ON drivers;
CREATE TRIGGER trg_create_wallet_for_driver
AFTER INSERT ON drivers
FOR EACH ROW
EXECUTE FUNCTION create_wallet_for_driver();

COMMIT;
