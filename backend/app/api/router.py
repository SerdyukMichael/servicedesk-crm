from fastapi import APIRouter
from app.api.endpoints import (
    auth,
    users,
    clients,
    equipment,
    tickets,
    work_templates,
    parts,
    vendors,
    invoices,
    notifications,
    service_catalog,
    product_catalog,
)

api_router = APIRouter()

api_router.include_router(auth.router,           prefix="/auth",           tags=["Авторизация"])
api_router.include_router(users.router,          prefix="/users",          tags=["Пользователи"])
api_router.include_router(clients.router,        prefix="/clients",        tags=["Клиенты"])
api_router.include_router(equipment.router,      prefix="/equipment",      tags=["Оборудование"])
api_router.include_router(tickets.router,        prefix="/tickets",        tags=["Заявки"])
api_router.include_router(work_templates.router, prefix="/work-templates", tags=["Шаблоны работ"])
api_router.include_router(parts.router,          prefix="/parts",          tags=["Склад"])
api_router.include_router(vendors.router,        prefix="/vendors",        tags=["Вендоры"])
api_router.include_router(invoices.router,       prefix="/invoices",       tags=["Счета"])
api_router.include_router(notifications.router,   prefix="/notifications",   tags=["Уведомления"])
api_router.include_router(service_catalog.router, prefix="/service-catalog", tags=["Прайс-лист услуг"])
api_router.include_router(product_catalog.router, prefix="/product-catalog", tags=["Прайс-лист товаров"])
