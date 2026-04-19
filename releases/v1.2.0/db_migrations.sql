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

