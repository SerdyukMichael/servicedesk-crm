from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Тест запускается без реальной БД — проверяем только структуру
def test_placeholder():
    """Заглушка — реальные тесты добавим в Фазе 6"""
    assert 1 + 1 == 2
