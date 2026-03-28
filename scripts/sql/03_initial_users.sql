-- ================================================================
-- Начальные пользователи системы
--
-- ВАЖНО: этот файл содержит ЗАГЛУШКУ пароля.
-- Используй scripts/seed.py для создания пользователей с реальным bcrypt-хешем:
--     cd backend && python ../scripts/seed.py
--
-- Этот SQL-файл предназначен только для справки / ручного восстановления.
-- Пароль для всех: ChangeMe123!  (хеш сгенерирован bcrypt, cost=12)
-- ================================================================
USE servicedesk;

-- Стандартный набор ролей согласно RBAC_Matrix.md
-- Роли: admin | sales_mgr | svc_mgr | engineer | warehouse | accountant | director

INSERT IGNORE INTO users
    (full_name, position, department, phone, email, roles, password_hash, status, is_active)
VALUES
    ('Системный администратор',      'Системный администратор',      'IT',          '+70000000000', 'admin@servicedesk.local',
     JSON_ARRAY('admin'),      '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCKul185zIcJPLMj2m.SiuG', 'active', 1),

    ('Руководитель сервиса',         'Руководитель сервисной службы','Сервис',      '+70000000001', 'svc_mgr@servicedesk.local',
     JSON_ARRAY('svc_mgr'),    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCKul185zIcJPLMj2m.SiuG', 'active', 1),

    ('Инженер Петров Иван',          'Инженер по обслуживанию',      'Сервис',      '+70000000002', 'engineer1@servicedesk.local',
     JSON_ARRAY('engineer'),   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCKul185zIcJPLMj2m.SiuG', 'active', 1),

    ('Инженер Сидорова Мария',       'Инженер по обслуживанию',      'Сервис',      '+70000000003', 'engineer2@servicedesk.local',
     JSON_ARRAY('engineer'),   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCKul185zIcJPLMj2m.SiuG', 'active', 1),

    ('Менеджер по продажам',         'Менеджер по работе с клиентами','Продажи',    '+70000000004', 'sales@servicedesk.local',
     JSON_ARRAY('sales_mgr'),  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCKul185zIcJPLMj2m.SiuG', 'active', 1),

    ('Кладовщик Склада',             'Кладовщик',                    'Склад',       '+70000000005', 'warehouse@servicedesk.local',
     JSON_ARRAY('warehouse'),  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCKul185zIcJPLMj2m.SiuG', 'active', 1),

    ('Директор',                     'Генеральный директор',          'Руководство', '+70000000006', 'director@servicedesk.local',
     JSON_ARRAY('director'),   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQyCKul185zIcJPLMj2m.SiuG', 'active', 1);

-- Триггер trg_user_after_insert автоматически создаёт notification_settings для каждого пользователя

SELECT CONCAT('Пользователей в системе: ', COUNT(*)) AS result FROM users WHERE is_deleted = 0;
