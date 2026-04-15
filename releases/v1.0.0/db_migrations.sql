-- Migration 010 -> 011: remove_product_catalog, add price_history
-- Applied on: production server (188.120.243.122)
-- Run: docker compose exec backend alembic upgrade head

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
