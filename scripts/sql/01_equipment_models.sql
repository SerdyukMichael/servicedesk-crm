-- ================================================================
-- Справочник моделей оборудования
-- Запуск: mysql -u sduser -p servicedesk < scripts/sql/01_equipment_models.sql
-- ================================================================
USE servicedesk;

INSERT IGNORE INTO equipment_models (name, manufacturer, warranty_period_months) VALUES
-- Принтеры карт Matica Technologies
('Matica XID 580i',               'Matica Technologies', 12),
('Matica XID 8600',               'Matica Technologies', 12),
('Matica MC110',                  'Matica Technologies', 12),
('Matica MC210',                  'Matica Technologies', 12),

-- Банкоматы NCR Corporation
('NCR SelfServ 84',               'NCR Corporation',     24),
('NCR SelfServ 87',               'NCR Corporation',     24),
('NCR SelfServ 6627',             'NCR Corporation',     24),
('NCR SelfServ 34',               'NCR Corporation',     24),

-- Банкоматы Diebold Nixdorf
('Diebold Nixdorf DN 200',        'Diebold Nixdorf',     24),
('Diebold Nixdorf DN 200i',       'Diebold Nixdorf',     24),
('Diebold Nixdorf ProCash 2050xe','Diebold Nixdorf',     24),
('Wincor Nixdorf ProCash 2100xe', 'Diebold Nixdorf',     24),

-- Банкоматы Nautilus Hyosung
('Nautilus Hyosung MX5600SE',     'Nautilus Hyosung',    12),
('Nautilus Hyosung MX8800',       'Nautilus Hyosung',    12),
('Nautilus Hyosung MX2800SE',     'Nautilus Hyosung',    12),

-- Платёжные терминалы
('Ingenico iSC Touch 480',        'Ingenico',            12),
('VeriFone MX 915',               'VeriFone',            12),
('VeriFone VX 820',               'VeriFone',            12);

SELECT CONCAT('Загружено моделей: ', COUNT(*)) AS result FROM equipment_models WHERE is_deleted = 0;
