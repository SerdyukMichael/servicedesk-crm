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

-- Running upgrade b2c3d4e5f6a1 -> 013_module5_warehouse

CREATE TABLE warehouses (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    name VARCHAR(255) NOT NULL, 
    type ENUM('company','bank') NOT NULL DEFAULT 'company', 
    client_id INTEGER, 
    is_active BOOL NOT NULL DEFAULT '1', 
    PRIMARY KEY (id), 
    FOREIGN KEY(client_id) REFERENCES clients (id) ON DELETE SET NULL
);

CREATE TABLE warehouse_stock (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    warehouse_id INTEGER NOT NULL, 
    part_id INTEGER NOT NULL, 
    quantity INTEGER NOT NULL DEFAULT '0', 
    unit_price_snapshot DECIMAL(12, 2), 
    PRIMARY KEY (id), 
    CONSTRAINT uq_warehouse_part UNIQUE (warehouse_id, part_id), 
    FOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE CASCADE, 
    FOREIGN KEY(part_id) REFERENCES spare_parts (id) ON DELETE CASCADE
);

CREATE TABLE stock_receipts (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    receipt_number VARCHAR(20) NOT NULL, 
    warehouse_id INTEGER NOT NULL, 
    receipt_date DATE NOT NULL, 
    vendor_id INTEGER, 
    supplier_doc_number VARCHAR(100), 
    notes TEXT, 
    status ENUM('draft','posted','cancelled') NOT NULL DEFAULT 'draft', 
    created_by INTEGER NOT NULL, 
    created_at DATETIME NOT NULL DEFAULT now(), 
    PRIMARY KEY (id), 
    UNIQUE (receipt_number), 
    FOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE RESTRICT, 
    FOREIGN KEY(vendor_id) REFERENCES vendors (id) ON DELETE SET NULL, 
    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_stock_receipts_receipt_number ON stock_receipts (receipt_number);

CREATE TABLE stock_receipt_items (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    receipt_id INTEGER NOT NULL, 
    part_id INTEGER NOT NULL, 
    quantity INTEGER NOT NULL, 
    unit_price DECIMAL(12, 2) NOT NULL DEFAULT '0', 
    PRIMARY KEY (id), 
    FOREIGN KEY(receipt_id) REFERENCES stock_receipts (id) ON DELETE CASCADE, 
    FOREIGN KEY(part_id) REFERENCES spare_parts (id) ON DELETE RESTRICT
);

CREATE TABLE parts_transfers (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    transfer_number VARCHAR(20) NOT NULL, 
    from_warehouse_id INTEGER NOT NULL, 
    to_warehouse_id INTEGER NOT NULL, 
    transfer_date DATE NOT NULL, 
    notes TEXT, 
    status ENUM('draft','posted','cancelled') NOT NULL DEFAULT 'draft', 
    created_by INTEGER NOT NULL, 
    posted_by INTEGER, 
    posted_at DATETIME, 
    created_at DATETIME NOT NULL DEFAULT now(), 
    PRIMARY KEY (id), 
    UNIQUE (transfer_number), 
    FOREIGN KEY(from_warehouse_id) REFERENCES warehouses (id) ON DELETE RESTRICT, 
    FOREIGN KEY(to_warehouse_id) REFERENCES warehouses (id) ON DELETE RESTRICT, 
    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT, 
    FOREIGN KEY(posted_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_parts_transfers_transfer_number ON parts_transfers (transfer_number);

CREATE TABLE parts_transfer_items (
    id INTEGER NOT NULL AUTO_INCREMENT, 
    transfer_id INTEGER NOT NULL, 
    part_id INTEGER NOT NULL, 
    quantity INTEGER NOT NULL, 
    unit_price_snapshot DECIMAL(12, 2), 
    PRIMARY KEY (id), 
    FOREIGN KEY(transfer_id) REFERENCES parts_transfers (id) ON DELETE CASCADE, 
    FOREIGN KEY(part_id) REFERENCES spare_parts (id) ON DELETE RESTRICT
);

ALTER TABLE work_act_items ADD COLUMN warehouse_id INTEGER;

ALTER TABLE work_act_items ADD FOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE SET NULL;

INSERT INTO warehouses (name, type, client_id, is_active) VALUES ('Основной склад', 'company', NULL, 1);

UPDATE alembic_version SET version_num='013_module5_warehouse' WHERE alembic_version.version_num = 'b2c3d4e5f6a1';

