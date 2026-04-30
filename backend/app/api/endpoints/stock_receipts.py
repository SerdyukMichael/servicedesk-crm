from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import StockReceipt, StockReceiptItem, Warehouse, WarehouseStock, SparePart, User
from app.api.deps import get_current_user, require_roles
from app.schemas import (
    StockReceiptCreate, StockReceiptUpdate, StockReceiptResponse,
    StockReceiptItemResponse, PaginatedResponse,
)
from app.services.audit import log_action

router = APIRouter()

_WRITE = ("admin", "svc_mgr")


def _next_receipt_number(db: Session) -> str:
    year = date.today().year
    count = db.query(StockReceipt).filter(
        StockReceipt.receipt_number.like(f"RCP-{year}-%")
    ).count()
    return f"RCP-{year}-{count + 1:04d}"


def _build_response(receipt: StockReceipt) -> StockReceiptResponse:
    items = []
    for item in receipt.items:
        items.append(StockReceiptItemResponse(
            id=item.id,
            part_id=item.part_id,
            part_name=item.part.name if item.part else "",
            part_sku=item.part.sku if item.part else "",
            quantity=item.quantity,
            unit_price=item.unit_price,
        ))
    return StockReceiptResponse(
        id=receipt.id,
        receipt_number=receipt.receipt_number,
        warehouse_id=receipt.warehouse_id,
        warehouse_name=receipt.warehouse.name if receipt.warehouse else "",
        receipt_date=receipt.receipt_date,
        vendor_id=receipt.vendor_id,
        supplier_doc_number=receipt.supplier_doc_number,
        notes=receipt.notes,
        status=receipt.status,
        created_by=receipt.created_by,
        created_at=receipt.created_at,
        items=items,
    )


@router.get("", response_model=PaginatedResponse[StockReceiptResponse])
def list_receipts(
    status: Optional[str] = Query(None),
    warehouse_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(StockReceipt).options(
        joinedload(StockReceipt.warehouse),
        joinedload(StockReceipt.items).joinedload(StockReceiptItem.part),
    )
    if status:
        q = q.filter(StockReceipt.status == status)
    if warehouse_id:
        q = q.filter(StockReceipt.warehouse_id == warehouse_id)
    total = q.count()
    skip = (page - 1) * size
    rows = q.order_by(StockReceipt.created_at.desc()).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=[_build_response(r) for r in rows],
                             total=total, page=page, size=size, pages=pages)


@router.post("", response_model=StockReceiptResponse, status_code=status.HTTP_201_CREATED)
def create_receipt(
    data: StockReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE)),
):
    wh = db.query(Warehouse).filter(Warehouse.id == data.warehouse_id, Warehouse.is_active.is_(True)).first()
    if not wh:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Склад не найден"})
    receipt = StockReceipt(
        receipt_number=_next_receipt_number(db),
        warehouse_id=data.warehouse_id,
        receipt_date=data.receipt_date,
        vendor_id=data.vendor_id,
        supplier_doc_number=data.supplier_doc_number,
        notes=data.notes,
        status="draft",
        created_by=current_user.id,
    )
    db.add(receipt)
    db.flush()
    for item_data in data.items:
        part = db.query(SparePart).filter(SparePart.id == item_data.part_id, SparePart.is_active.is_(True)).first()
        if not part:
            raise HTTPException(status.HTTP_404_NOT_FOUND,
                                detail={"error": "NOT_FOUND", "message": f"Запчасть id={item_data.part_id} не найдена"})
        db.add(StockReceiptItem(
            receipt_id=receipt.id,
            part_id=item_data.part_id,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
        ))
    db.commit()
    db.refresh(receipt)
    return _build_response(receipt)


@router.get("/{receipt_id}", response_model=StockReceiptResponse)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    receipt = db.query(StockReceipt).options(
        joinedload(StockReceipt.warehouse),
        joinedload(StockReceipt.items).joinedload(StockReceiptItem.part),
    ).filter(StockReceipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Приходный ордер не найден"})
    return _build_response(receipt)


@router.put("/{receipt_id}", response_model=StockReceiptResponse)
def update_receipt(
    receipt_id: int,
    data: StockReceiptUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE)),
):
    receipt = db.query(StockReceipt).options(
        joinedload(StockReceipt.warehouse),
        joinedload(StockReceipt.items).joinedload(StockReceiptItem.part),
    ).filter(StockReceipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Приходный ордер не найден"})
    if receipt.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail={"error": "STATUS_ERROR", "message": "Изменение возможно только в статусе draft"})
    update_data = data.model_dump(exclude_none=True, exclude={"items"})
    for k, v in update_data.items():
        setattr(receipt, k, v)
    if data.items is not None:
        for old_item in list(receipt.items):
            db.delete(old_item)
        db.flush()
        for item_data in data.items:
            db.add(StockReceiptItem(
                receipt_id=receipt.id,
                part_id=item_data.part_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
            ))
    db.commit()
    db.refresh(receipt)
    return _build_response(receipt)


@router.post("/{receipt_id}/post", response_model=StockReceiptResponse)
def post_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE)),
):
    receipt = db.query(StockReceipt).options(
        joinedload(StockReceipt.warehouse),
        joinedload(StockReceipt.items).joinedload(StockReceiptItem.part),
    ).filter(StockReceipt.id == receipt_id).with_for_update().first()
    if not receipt:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Приходный ордер не найден"})
    if receipt.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail={"error": "STATUS_ERROR", "message": "Провести можно только черновик"})
    if not receipt.items:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"error": "VALIDATION", "message": "Добавьте хотя бы одну запчасть"})
    wh = db.query(Warehouse).filter(Warehouse.id == receipt.warehouse_id, Warehouse.is_active.is_(True)).first()
    if not wh:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"error": "VALIDATION", "message": "Склад недоступен"})

    for item in receipt.items:
        if item.quantity < 1:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail={"error": "VALIDATION", "message": "Количество должно быть не менее 1"})
        stock = (
            db.query(WarehouseStock)
            .filter(WarehouseStock.warehouse_id == receipt.warehouse_id,
                    WarehouseStock.part_id == item.part_id)
            .with_for_update()
            .first()
        )
        if stock:
            stock.quantity += item.quantity
            stock.unit_price_snapshot = item.unit_price
        else:
            db.add(WarehouseStock(
                warehouse_id=receipt.warehouse_id,
                part_id=item.part_id,
                quantity=item.quantity,
                unit_price_snapshot=item.unit_price,
            ))
        # keep SparePart.quantity in sync for company warehouse
        if wh.type == "company":
            part = db.query(SparePart).filter(SparePart.id == item.part_id).first()
            if part:
                part.quantity += item.quantity
                part.unit_price = item.unit_price

    receipt.status = "posted"
    db.commit()
    log_action(db, current_user.id, "POST", "stock_receipt", receipt.id,
               new={"receipt_number": receipt.receipt_number})
    db.refresh(receipt)
    return _build_response(receipt)


@router.post("/{receipt_id}/cancel", response_model=StockReceiptResponse)
def cancel_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE)),
):
    receipt = db.query(StockReceipt).filter(StockReceipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Приходный ордер не найден"})
    if receipt.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail={"error": "STATUS_ERROR",
                                    "message": "Нельзя отменить проведённый приход"})
    receipt.status = "cancelled"
    db.commit()
    db.refresh(receipt)
    return _build_response(receipt)
