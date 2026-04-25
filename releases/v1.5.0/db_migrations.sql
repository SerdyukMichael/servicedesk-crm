CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 001

ALTER TABLE clients MODIFY contract_type VARCHAR(64) NOT NULL DEFAULT 'none';

ALTER TABLE clients ADD COLUMN city VARCHAR(128);

INSERT INTO alembic_version (version_num) VALUES ('001');

-- Running upgrade 001 -> 002

ALTER TABLE clients ADD COLUMN contract_start DATE;

UPDATE alembic_version SET version_num='002' WHERE alembic_version.version_num = '001';

-- Running upgrade 002 -> 003

CREATE TABLE ticket_status_history (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    ticket_id INTEGER NOT NULL, 
    from_status VARCHAR(32), 
    to_status VARCHAR(32) NOT NULL, 
    changed_by INTEGER, 
    comment TEXT, 
    changed_at DATETIME NOT NULL DEFAULT NOW(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(ticket_id) REFERENCES tickets (id) ON DELETE CASCADE, 
    FOREIGN KEY(changed_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_tsh_ticket_id ON ticket_status_history (ticket_id);

UPDATE alembic_version SET version_num='003' WHERE alembic_version.version_num = '002';

-- Running upgrade 003 -> 004

ALTER TABLE equipment ADD COLUMN manufacture_date DATE;

ALTER TABLE equipment ADD COLUMN sale_date DATE;

ALTER TABLE equipment ADD COLUMN warranty_start DATE;

ALTER TABLE equipment ADD COLUMN firmware_version VARCHAR(64);

ALTER TABLE equipment MODIFY COLUMN status ENUM('active','in_repair','decommissioned','written_off','transferred') NOT NULL DEFAULT 'active';

UPDATE alembic_version SET version_num='004' WHERE alembic_version.version_num = '003';

-- Running upgrade 004 -> 005

ALTER TABLE repair_history ADD COLUMN parts_used JSON;

UPDATE alembic_version SET version_num='005' WHERE alembic_version.version_num = '004';

-- Running upgrade 005 -> 006

ALTER TABLE equipment_models ADD COLUMN warranty_months_default INTEGER;

UPDATE alembic_version SET version_num='006' WHERE alembic_version.version_num = '005';

-- Running upgrade 006 -> 007

ALTER TABLE client_contacts ADD COLUMN is_primary BOOL NOT NULL DEFAULT false;

ALTER TABLE client_contacts ADD COLUMN portal_access BOOL NOT NULL DEFAULT false;

ALTER TABLE client_contacts ADD COLUMN portal_role ENUM('client_user','client_admin');

ALTER TABLE client_contacts ADD COLUMN created_by INTEGER;

ALTER TABLE client_contacts ADD FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL;

ALTER TABLE client_contacts ADD COLUMN created_at DATETIME NOT NULL DEFAULT now();

ALTER TABLE client_contacts ADD COLUMN updated_at DATETIME NOT NULL DEFAULT now();

UPDATE alembic_version SET version_num='007' WHERE alembic_version.version_num = '006';

-- Running upgrade 007 -> 008

ALTER TABLE users ADD COLUMN client_id INTEGER;

ALTER TABLE users ADD FOREIGN KEY(client_id) REFERENCES clients (id) ON DELETE SET NULL;

ALTER TABLE client_contacts ADD COLUMN portal_user_id INTEGER;

ALTER TABLE client_contacts ADD FOREIGN KEY(portal_user_id) REFERENCES users (id) ON DELETE SET NULL;

UPDATE alembic_version SET version_num='008' WHERE alembic_version.version_num = '007';

-- Running upgrade 008 -> 009

ALTER TABLE ticket_comments ADD COLUMN is_internal BOOL NOT NULL DEFAULT false;

UPDATE alembic_version SET version_num='009' WHERE alembic_version.version_num = '008';

-- Running upgrade 009 -> 6cd8b51a3e8b

CREATE TABLE service_catalog (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    code VARCHAR(32) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    description TEXT, 
    category ENUM('repair','maintenance','diagnostics','visit','other') NOT NULL, 
    unit ENUM('pcs','hour','visit','kit') NOT NULL, 
    unit_price DECIMAL(12, 2) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    is_active BOOL NOT NULL, 
    created_at DATETIME NOT NULL, 
    updated_at DATETIME NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_service_catalog_code ON service_catalog (code);

CREATE TABLE work_act_items (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    work_act_id INTEGER NOT NULL, 
    item_type ENUM('service','part') NOT NULL, 
    service_id INTEGER, 
    part_id INTEGER, 
    name VARCHAR(255) NOT NULL, 
    quantity DECIMAL(10, 3) NOT NULL, 
    unit VARCHAR(16) NOT NULL, 
    unit_price DECIMAL(12, 2) NOT NULL, 
    total DECIMAL(14, 2) NOT NULL, 
    sort_order INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(part_id) REFERENCES spare_parts (id) ON DELETE RESTRICT, 
    FOREIGN KEY(service_id) REFERENCES service_catalog (id) ON DELETE RESTRICT, 
    FOREIGN KEY(work_act_id) REFERENCES work_acts (id) ON DELETE CASCADE
);

ALTER TABLE invoice_items ADD COLUMN item_type ENUM('service','part','manual');

ALTER TABLE invoice_items ADD COLUMN service_id INTEGER;

ALTER TABLE invoice_items ADD COLUMN part_id INTEGER;

ALTER TABLE invoice_items ADD FOREIGN KEY(part_id) REFERENCES spare_parts (id) ON DELETE RESTRICT;

ALTER TABLE invoice_items ADD FOREIGN KEY(service_id) REFERENCES service_catalog (id) ON DELETE RESTRICT;

UPDATE alembic_version SET version_num='6cd8b51a3e8b' WHERE alembic_version.version_num = '009';

-- Running upgrade 6cd8b51a3e8b -> 010

CREATE TABLE product_catalog (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    code VARCHAR(32) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    description TEXT, 
    category ENUM('spare_part','other') NOT NULL DEFAULT 'other', 
    unit ENUM('pcs','pack','kit') NOT NULL DEFAULT 'pcs', 
    unit_price DECIMAL(12, 2) NOT NULL DEFAULT '0', 
    currency VARCHAR(3) NOT NULL DEFAULT 'RUB', 
    is_active BOOL NOT NULL DEFAULT '1', 
    created_at DATETIME NOT NULL, 
    updated_at DATETIME NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_product_catalog_code ON product_catalog (code);

ALTER TABLE work_act_items ADD COLUMN product_id INTEGER;

ALTER TABLE work_act_items ADD CONSTRAINT fk_work_act_items_product_id FOREIGN KEY(product_id) REFERENCES product_catalog (id) ON DELETE RESTRICT;

ALTER TABLE work_act_items MODIFY item_type ENUM('service','part','product') NOT NULL;

ALTER TABLE invoice_items ADD COLUMN product_id INTEGER;

ALTER TABLE invoice_items ADD CONSTRAINT fk_invoice_items_product_id FOREIGN KEY(product_id) REFERENCES product_catalog (id) ON DELETE RESTRICT;

ALTER TABLE invoice_items MODIFY item_type ENUM('service','part','product','manual') NULL;

UPDATE alembic_version SET version_num='010' WHERE alembic_version.version_num = '6cd8b51a3e8b';

-- Running upgrade 010 -> 011

ALTER TABLE work_act_items DROP FOREIGN KEY fk_work_act_items_product_id;

ALTER TABLE work_act_items DROP COLUMN product_id;

ALTER TABLE work_act_items MODIFY item_type ENUM('service','part') NOT NULL;

ALTER TABLE invoice_items DROP FOREIGN KEY fk_invoice_items_product_id;

ALTER TABLE invoice_items DROP COLUMN product_id;

ALTER TABLE invoice_items MODIFY item_type ENUM('service','part','manual') NULL;

DROP INDEX ix_product_catalog_code ON product_catalog;

DROP TABLE product_catalog;

ALTER TABLE spare_parts ADD COLUMN created_by INTEGER;

ALTER TABLE spare_parts ADD CONSTRAINT fk_spare_parts_created_by FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL;

ALTER TABLE spare_parts ADD COLUMN created_at DATETIME NOT NULL DEFAULT NOW();

ALTER TABLE spare_parts ADD COLUMN updated_at DATETIME NOT NULL DEFAULT NOW();

CREATE TABLE price_history (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    entity_type ENUM('service','spare_part') NOT NULL, 
    entity_id INTEGER NOT NULL, 
    old_price DECIMAL(12, 2) NOT NULL, 
    new_price DECIMAL(12, 2) NOT NULL, 
    currency VARCHAR(3) NOT NULL DEFAULT 'RUB', 
    reason VARCHAR(512) NOT NULL, 
    changed_by INTEGER NOT NULL, 
    changed_at DATETIME NOT NULL DEFAULT NOW(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(changed_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_price_history_entity ON price_history (entity_type, entity_id);

UPDATE alembic_version SET version_num='011' WHERE alembic_version.version_num = '010';

-- Running upgrade 011 -> b31f1f38108d

UPDATE invoices i
        JOIN (
            SELECT invoice_id, SUM(total) AS items_total
            FROM invoice_items
            GROUP BY invoice_id
        ) ii ON i.id = ii.invoice_id
        SET
            i.vat_rate     = 22.00,
            i.total_amount = ii.items_total,
            i.vat_amount   = ROUND(ii.items_total * 22 / 122, 2),
            i.subtotal     = ROUND(ii.items_total - ROUND(ii.items_total * 22 / 122, 2), 2);

UPDATE alembic_version SET version_num='b31f1f38108d' WHERE alembic_version.version_num = '011';

-- Running upgrade b31f1f38108d -> d20b1718df8a

UPDATE invoices i
        JOIN (
            SELECT invoice_id, SUM(total) AS items_total
            FROM invoice_items
            GROUP BY invoice_id
        ) ii ON i.id = ii.invoice_id
        SET
            i.vat_rate     = 22.00,
            i.total_amount = ii.items_total,
            i.vat_amount   = ROUND(ii.items_total * 22 / 122, 2),
            i.subtotal     = ROUND(ii.items_total - ROUND(ii.items_total * 22 / 122, 2), 2);

UPDATE alembic_version SET version_num='d20b1718df8a' WHERE alembic_version.version_num = 'b31f1f38108d';

-- Running upgrade d20b1718df8a -> 89b7f086cd94

UPDATE invoices SET vat_rate = 22.00;

UPDATE invoices i
        JOIN (
            SELECT invoice_id, SUM(total) AS s
            FROM invoice_items
            GROUP BY invoice_id
        ) ii ON i.id = ii.invoice_id
        SET
            i.total_amount = ii.s,
            i.vat_amount   = ROUND(ii.s * 22 / 122, 2),
            i.subtotal     = ROUND(ii.s - ROUND(ii.s * 22 / 122, 2), 2);

UPDATE invoices i
        LEFT JOIN invoice_items ii ON ii.invoice_id = i.id
        SET
            i.vat_amount = ROUND(i.total_amount * 22 / 122, 2),
            i.subtotal   = ROUND(i.total_amount - ROUND(i.total_amount * 22 / 122, 2), 2)
        WHERE ii.invoice_id IS NULL;

UPDATE alembic_version SET version_num='89b7f086cd94' WHERE alembic_version.version_num = 'd20b1718df8a';

-- Running upgrade 89b7f086cd94 -> 012_system_settings

CREATE TABLE system_settings (
    `key` VARCHAR(64) NOT NULL, 
    value VARCHAR(255) NOT NULL, 
    updated_at DATETIME NOT NULL DEFAULT now(), 
    updated_by INTEGER, 
    PRIMARY KEY (`key`), 
    FOREIGN KEY(updated_by) REFERENCES users (id) ON DELETE SET NULL
);

INSERT INTO system_settings (`key`, value) VALUES ('currency_code', 'RUB'), ('currency_name', 'Российский рубль');

UPDATE alembic_version SET version_num='012_system_settings' WHERE alembic_version.version_num = '89b7f086cd94';

-- Running upgrade 012_system_settings -> 403d0220d2a5

DROP TABLE repair_history;

UPDATE alembic_version SET version_num='403d0220d2a5' WHERE alembic_version.version_num = '012_system_settings';

-- Running upgrade 403d0220d2a5 -> 630140d83c77

CREATE TABLE exchange_rates (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    currency VARCHAR(3) NOT NULL, 
    rate DECIMAL(15, 4) NOT NULL, 
    set_by INTEGER NOT NULL, 
    set_at DATETIME NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(set_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_exchange_rates_currency ON exchange_rates (currency);

UPDATE alembic_version SET version_num='630140d83c77' WHERE alembic_version.version_num = '403d0220d2a5';

-- Running upgrade 630140d83c77 -> e6dad3b055f1

ALTER TABLE exchange_rates ADD COLUMN created_at DATETIME NOT NULL DEFAULT NOW();

UPDATE alembic_version SET version_num='e6dad3b055f1' WHERE alembic_version.version_num = '630140d83c77';

-- Running upgrade e6dad3b055f1 -> f1a2b3c4d5e6

ALTER TABLE tickets ADD COLUMN assigned_at DATETIME;

ALTER TABLE tickets ADD COLUMN sla_reaction_deadline DATETIME;

ALTER TABLE tickets ADD COLUMN sla_resolution_deadline DATETIME;

ALTER TABLE tickets ADD COLUMN sla_reaction_violated BOOL NOT NULL DEFAULT '0';

ALTER TABLE tickets ADD COLUMN sla_resolution_violated BOOL NOT NULL DEFAULT '0';

ALTER TABLE tickets ADD COLUMN sla_reaction_escalated_at DATETIME;

ALTER TABLE tickets ADD COLUMN sla_resolution_escalated_at DATETIME;

CREATE INDEX ix_tickets_sla_reaction_deadline ON tickets (sla_reaction_deadline);

CREATE INDEX ix_tickets_sla_resolution_deadline ON tickets (sla_resolution_deadline);

UPDATE alembic_version SET version_num='f1a2b3c4d5e6' WHERE alembic_version.version_num = 'e6dad3b055f1';

-- Running upgrade f1a2b3c4d5e6 -> a1b2c3d4e5f6

CREATE INDEX ix_audit_log_created_at ON audit_log (created_at);

CREATE INDEX ix_audit_log_user_id ON audit_log (user_id);

CREATE INDEX ix_audit_log_entity_type ON audit_log (entity_type);

CREATE INDEX ix_audit_log_action ON audit_log (action);

UPDATE alembic_version SET version_num='a1b2c3d4e5f6' WHERE alembic_version.version_num = 'f1a2b3c4d5e6';

-- Running upgrade a1b2c3d4e5f6 -> b2c3d4e5f6a1

CREATE TABLE maintenance_schedules (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    equipment_id INTEGER NOT NULL, 
    frequency ENUM('monthly','quarterly','semiannual','annual') NOT NULL, 
    first_date DATE NOT NULL, 
    next_date DATE NOT NULL, 
    last_ticket_id INTEGER, 
    is_active BOOL NOT NULL DEFAULT '1', 
    created_by INTEGER, 
    created_at DATETIME NOT NULL DEFAULT NOW(), 
    updated_at DATETIME NOT NULL DEFAULT NOW(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(equipment_id) REFERENCES equipment (id) ON DELETE CASCADE, 
    FOREIGN KEY(last_ticket_id) REFERENCES tickets (id) ON DELETE SET NULL, 
    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_maintenance_schedules_equipment_id ON maintenance_schedules (equipment_id);

CREATE INDEX ix_maintenance_schedules_next_date ON maintenance_schedules (next_date);

CREATE INDEX ix_maint_active_next ON maintenance_schedules (is_active, next_date);

UPDATE alembic_version SET version_num='b2c3d4e5f6a1' WHERE alembic_version.version_num = 'a1b2c3d4e5f6';

