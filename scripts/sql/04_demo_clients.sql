-- ================================================================
-- Демо-клиенты для тестирования системы
-- Запуск: mysql -u sduser -p servicedesk < scripts/sql/04_demo_clients.sql
-- ================================================================
USE servicedesk;

INSERT IGNORE INTO clients (name, contract_type, contract_number, contract_valid_until, address) VALUES
('ПАО Сбербанк',          'premium',  'SD-2026-001', '2027-12-31', 'г. Москва, ул. Вавилова, д. 19'),
('ВТБ Банк (ПАО)',         'premium',  'SD-2026-002', '2027-06-30', 'г. Москва, ул. Мясницкая, д. 35'),
('АО Альфа-Банк',          'standard', 'SD-2026-003', '2026-12-31', 'г. Москва, ул. Каланчёвская, д. 27'),
('ПАО Росбанк',            'standard', 'SD-2026-004', '2026-09-30', 'г. Москва, Сухаревская пл., д. 1'),
('КБ Тестовый (демо)',      'none',     NULL,          NULL,          'г. Москва, ул. Тестовая, д. 1');

-- Демо-контакты для клиентов
INSERT IGNORE INTO client_contacts (client_id, name, phone, email, is_active)
SELECT c.id, 'Иванов Алексей Борисович', '+74951234567', 'ivanov@sberbank.ru', 1
FROM clients c WHERE c.name = 'ПАО Сбербанк';

INSERT IGNORE INTO client_contacts (client_id, name, phone, email, is_active)
SELECT c.id, 'Петрова Ольга Сергеевна', '+74952345678', 'petrova@vtb.ru', 1
FROM clients c WHERE c.name = 'ВТБ Банк (ПАО)';

SELECT CONCAT('Клиентов в системе: ', COUNT(*)) AS result FROM clients WHERE is_deleted = 0;
