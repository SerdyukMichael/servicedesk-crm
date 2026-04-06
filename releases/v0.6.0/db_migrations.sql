time="2026-04-06T20:10:14+03:00" level=warning msg="The \"MYSQL_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2026-04-06T20:10:14+03:00" level=warning msg="The \"MYSQL_ROOT_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2026-04-06T20:10:14+03:00" level=warning msg="The \"REDIS_PASSWORD\" variable is not set. Defaulting to a blank string."
time="2026-04-06T20:10:14+03:00" level=warning msg="The \"REDIS_PASSWORD\" variable is not set. Defaulting to a blank string."
INFO  [alembic.runtime.migration] Context impl MySQLImpl.
INFO  [alembic.runtime.migration] Generating static SQL
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INFO  [alembic.runtime.migration] Running upgrade  -> 001, clients: contract_type VARCHAR, add city
-- Running upgrade  -> 001

ALTER TABLE clients MODIFY contract_type VARCHAR(64) NOT NULL DEFAULT 'none';

ALTER TABLE clients ADD COLUMN city VARCHAR(128);

INSERT INTO alembic_version (version_num) VALUES ('001');

INFO  [alembic.runtime.migration] Running upgrade 001 -> 002, clients: add contract_start column
-- Running upgrade 001 -> 002

ALTER TABLE clients ADD COLUMN contract_start DATE;

UPDATE alembic_version SET version_num='002' WHERE alembic_version.version_num = '001';

-- Running upgrade 002 -> 003

INFO  [alembic.runtime.migration] Running upgrade 002 -> 003, tickets: add ticket_status_history table
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

INFO  [alembic.runtime.migration] Running upgrade 003 -> 004, equipment: add passport fields (manufacture_date, sale_date, warranty_start,
firmware_version) and extend status enum with 'transferred'
-- Running upgrade 003 -> 004

ALTER TABLE equipment ADD COLUMN manufacture_date DATE;

ALTER TABLE equipment ADD COLUMN sale_date DATE;

ALTER TABLE equipment ADD COLUMN warranty_start DATE;

ALTER TABLE equipment ADD COLUMN firmware_version VARCHAR(64);

ALTER TABLE equipment MODIFY COLUMN status ENUM('active','in_repair','decommissioned','written_off','transferred') NOT NULL DEFAULT 'active';

INFO  [alembic.runtime.migration] Running upgrade 004 -> 005, repair_history: add parts_used JSON column
UPDATE alembic_version SET version_num='004' WHERE alembic_version.version_num = '003';

-- Running upgrade 004 -> 005

ALTER TABLE repair_history ADD COLUMN parts_used JSON;

UPDATE alembic_version SET version_num='005' WHERE alembic_version.version_num = '004';

INFO  [alembic.runtime.migration] Running upgrade 005 -> 006, equipment_models: add warranty_months_default column
-- Running upgrade 005 -> 006

ALTER TABLE equipment_models ADD COLUMN warranty_months_default INTEGER;

UPDATE alembic_version SET version_num='006' WHERE alembic_version.version_num = '005';

-- Running upgrade 006 -> 007

INFO  [alembic.runtime.migration] Running upgrade 006 -> 007, client_contacts: add is_primary, portal_access, portal_role, created_by, timestamps
ALTER TABLE client_contacts ADD COLUMN is_primary BOOL NOT NULL DEFAULT false;

ALTER TABLE client_contacts ADD COLUMN portal_access BOOL NOT NULL DEFAULT false;

ALTER TABLE client_contacts ADD COLUMN portal_role ENUM('client_user','client_admin');

ALTER TABLE client_contacts ADD COLUMN created_by INTEGER;

ALTER TABLE client_contacts ADD FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL;

ALTER TABLE client_contacts ADD COLUMN created_at DATETIME NOT NULL DEFAULT now();

ALTER TABLE client_contacts ADD COLUMN updated_at DATETIME NOT NULL DEFAULT now();

UPDATE alembic_version SET version_num='007' WHERE alembic_version.version_num = '006';

INFO  [alembic.runtime.migration] Running upgrade 007 -> 008, users: add client_id; client_contacts: add portal_user_id
-- Running upgrade 007 -> 008

ALTER TABLE users ADD COLUMN client_id INTEGER;

ALTER TABLE users ADD FOREIGN KEY(client_id) REFERENCES clients (id) ON DELETE SET NULL;

ALTER TABLE client_contacts ADD COLUMN portal_user_id INTEGER;

ALTER TABLE client_contacts ADD FOREIGN KEY(portal_user_id) REFERENCES users (id) ON DELETE SET NULL;

UPDATE alembic_version SET version_num='008' WHERE alembic_version.version_num = '007';

-- Running upgrade 008 -> 009

INFO  [alembic.runtime.migration] Running upgrade 008 -> 009, ticket_comments_is_internal
ALTER TABLE ticket_comments ADD COLUMN is_internal BOOL NOT NULL DEFAULT false;

UPDATE alembic_version SET version_num='009' WHERE alembic_version.version_num = '008';

