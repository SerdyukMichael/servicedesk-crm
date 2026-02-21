from fastapi import APIRouter
from app.api.endpoints import auth, users, clients, equipment, requests, parts, invoices, vendors

api_router = APIRouter()

api_router.include_router(auth.router,      prefix="/auth",             tags=["Авторизация"])
api_router.include_router(users.router,     prefix="/users",            tags=["Пользователи"])
api_router.include_router(clients.router,   prefix="/clients",          tags=["Клиенты"])
api_router.include_router(equipment.router, prefix="/equipment",        tags=["Оборудование"])
api_router.include_router(requests.router,  prefix="/requests",         tags=["Заявки"])
api_router.include_router(parts.router,     prefix="/parts",            tags=["Склад"])
api_router.include_router(invoices.router,  prefix="/invoices",         tags=["Счета"])
api_router.include_router(vendors.router,   prefix="/vendors",          tags=["Вендоры"])
