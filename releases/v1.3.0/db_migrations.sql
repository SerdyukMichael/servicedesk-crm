-- Running upgrade 012_system_settings -> 403d0220d2a5

DROP TABLE repair_history;

UPDATE alembic_version SET version_num='403d0220d2a5' WHERE alembic_version.version_num = '012_system_settings';
