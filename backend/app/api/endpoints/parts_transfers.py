from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import (
    PartsTransfer, PartsTransferItem, Warehouse, WarehouseStock, SparePart, User,
)
from app.api.deps import get_current_user, require_roles
from app.schemas import (
    PartsTransferCreate, PartsTransferUpdate, PartsTransferResponse,
    PartsTransferItemResponse, PaginatedResponse,
)
from app.services.audit import log_action

router = APIRouter()

_WRITE = ("admin", "svc_mgr")


def _next_transfer_number(db: Session) -> str:
    year = date.today().year
    count = db.query(PartsTransfer).filter(
        PartsTransfer.transfer_number.like(f"TRF-{year}-%")
    ).count()
    return f"TRF-{year}-{count + 1:04d}"


def _build_response(transfer: PartsTransfer, db: Session) -> PartsTransferResponse:
    items = []
    for item in transfer.items:
        stock = db.query(WarehouseStock).filter(
            WarehouseStock.warehouse_id == transfer.from_warehouse_id,
            WarehouseStock.part_id == item.part_id,
        ).first()
        items.append(PartsTransferItemResponse(
            id=item.id,
            part_id=item.part_id,
            part_name=item.part.name if item.part else "",
            part_sku=item.part.sku if item.part else "",
            quantity=item.quantity,
            unit_price_snapshot=item.unit_price_snapshot,
            available_qty=stock.quantity if stock else 0,
        ))
    return PartsTransferResponse(
        id=transfer.id,
        transfer_number=transfer.transfer_number,
        from_warehouse_id=transfer.from_warehouse_id,
        from_warehouse_name=transfer.from_warehouse.name if transfer.from_warehouse else "",
        to_warehouse_id=transfer.to_warehouse_id,
        to_warehouse_name=transfer.to_warehouse.name if transfer.to_warehouse else "",
        transfer_date=transfer.transfer_date,
        notes=transfer.notes,
        status=transfer.status,
        created_by=transfer.created_by,
        posted_by=transfer.posted_by,
        posted_at=transfer.posted_at,
        created_at=transfer.created_at,
        items=items,
    )


def _load_transfer(db: Session, transfer_id: int) -> PartsTransfer:
    return (
        db.query(PartsTransfer)
        .options(
            joinedload(PartsTransfer.from_warehouse),
            joinedload(PartsTransfer.to_warehouse),
            joinedload(PartsTransfer.items).joinedload(PartsTransferItem.part),
        )
        .filter(PartsTransfer.id == transfer_id)
        .first()
    )


@router.get("", response_model=PaginatedResponse[PartsTransferResponse])
def list_transfers(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(PartsTransfer).options(
        joinedload(PartsTransfer.from_warehouse),
        joinedload(PartsTransfer.to_warehouse),
        joinedload(PartsTransfer.items).joinedload(PartsTransferItem.part),
    )
    if status:
        q = q.filter(PartsTransfer.status == status)
    total = q.count()
    skip = (page - 1) * size
    rows = q.order_by(PartsTransfer.created_at.desc()).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(
        items=[_build_response(r, db) for r in rows],
        total=total, page=page, size=size, pages=pages,
    )


@router.post("", response_model=PartsTransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    data: PartsTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE)),
):
    from_wh = db.query(Warehouse).filter(Warehouse.id == data.from_warehouse_id, Warehouse.is_active.is_(True)).first()
    to_wh = db.query(Warehouse).filter(Warehouse.id == data.to_warehouse_id, Warehouse.is_active.is_(True)).first()
    if not from_wh or not to_wh:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Склад не найден"})

    transfer = PartsTransfer(
        transfer_number=_next_transfer_number(db),
        from_warehouse_id=data.from_warehouse_id,
        to_warehouse_id=data.to_warehouse_id,
        transfer_date=data.transfer_date,
        notes=data.notes,
        status="draft",
        created_by=current_user.id,
    )
    db.add(transfer)
    db.flush()
    for item_data in data.items:
        part = db.query(SparePart).filter(SparePart.id == item_data.part_id, SparePart.is_active.is_(True)).first()
        if not part:
            raise HTTPException(status.HTTP_404_NOT_FOUND,
                                detail={"error": "NOT_FOUND", "message": f"Запчасть id={item_data.part_id} не найдена"})
        db.add(PartsTransferItem(
            transfer_id=transfer.id,
            part_id=item_data.part_id,
            quantity=item_data.quantity,
            unit_price_snapshot=part.unit_price,
        ))
    db.commit()
    transfer = _load_transfer(db, transfer.id)
    return _build_response(transfer, db)


@router.get("/{transfer_id}", response_model=PartsTransferResponse)
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    transfer = _load_transfer(db, transfer_id)
    if not transfer:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Передача не найдена"})
    return _build_response(transfer, db)


@router.put("/{transfer_id}", response_model=PartsTransferResponse)
def update_transfer(
    transfer_id: int,
    data: PartsTransferUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE)),
):
    transfer = _load_transfer(db, transfer_id)
    if not transfer:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Передача не найдена"})
    if transfer.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail={"error": "STATUS_ERROR", "message": "Изменение возможно только в статусе draft"})
    update_data = data.model_dump(exclude_none=True, exclude={"items"})
    for k, v in update_data.items():
        setattr(transfer, k, v)
    if data.items is not None:
        for old_item in list(transfer.items):
            db.delete(old_item)
        db.flush()
        for item_data in data.items:
            part = db.query(SparePart).filter(SparePart.id == item_data.part_id).first()
            db.add(PartsTransferItem(
                transfer_id=transfer.id,
                part_id=item_data.part_id,
                quantity=item_data.quantity,
                unit_price_snapshot=part.unit_price if part else None,
            ))
    db.commit()
    transfer = _load_transfer(db, transfer.id)
    return _build_response(transfer, db)


@router.post("/{transfer_id}/post", response_model=PartsTransferResponse)
def post_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE)),
):
    transfer = _load_transfer(db, transfer_id)
    if not transfer:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Передача не найдена"})
    if transfer.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail={"error": "STATUS_ERROR", "message": "Провести можно только черновик"})
    if not transfer.items:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"error": "VALIDATION", "message": "Добавьте хотя бы одну запчасть"})
    if transfer.from_warehouse_id == transfer.to_warehouse_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"error": "VALIDATION",
                                    "message": "Склад-источник и получатель должны быть разными"})
    to_wh = db.query(Warehouse).filter(Warehouse.id == transfer.to_warehouse_id).first()
    if not to_wh or to_wh.type != "bank":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"error": "VALIDATION", "message": "Получатель должен быть складом банка"})
    from_wh = db.query(Warehouse).filter(Warehouse.id == transfer.from_warehouse_id).first()

    # lock source stock rows
    for item in transfer.items:
        if item.quantity < 1:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail={"error": "VALIDATION", "message": "Количество должно быть не менее 1"})
        src_stock = (
            db.query(WarehouseStock)
            .filter(WarehouseStock.warehouse_id == transfer.from_warehouse_id,
                    WarehouseStock.part_id == item.part_id)
            .with_for_update()
            .first()
        )
        available = src_stock.quantity if src_stock else 0
        if available < item.quantity:
            part_name = item.part.name if item.part else str(item.part_id)
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail={"error": "INSUFFICIENT_STOCK",
                                        "message": f"Недостаточно запчастей {part_name} на складе-источнике: "
                                                   f"доступно {available}, запрошено {item.quantity}"})

    # apply
    for item in transfer.items:
        src_stock = (
            db.query(WarehouseStock)
            .filter(WarehouseStock.warehouse_id == transfer.from_warehouse_id,
                    WarehouseStock.part_id == item.part_id)
            .first()
        )
        src_stock.quantity -= item.quantity

        dst_stock = (
            db.query(WarehouseStock)
            .filter(WarehouseStock.warehouse_id == transfer.to_warehouse_id,
                    WarehouseStock.part_id == item.part_id)
            .first()
        )
        if dst_stock:
            dst_stock.quantity += item.quantity
        else:
            db.add(WarehouseStock(
                warehouse_id=transfer.to_warehouse_id,
                part_id=item.part_id,
                quantity=item.quantity,
                unit_price_snapshot=item.unit_price_snapshot,
            ))

        # sync SparePart.quantity for company warehouse
        if from_wh and from_wh.type == "company":
            part = db.query(SparePart).filter(SparePart.id == item.part_id).first()
            if part:
                part.quantity = max(0, part.quantity - item.quantity)

    transfer.status = "posted"
    transfer.posted_by = current_user.id
    transfer.posted_at = datetime.utcnow()
    db.commit()
    log_action(db, current_user.id, "POST", "parts_transfer", transfer.id,
               new={"transfer_number": transfer.transfer_number})
    transfer = _load_transfer(db, transfer.id)
    return _build_response(transfer, db)


@router.post("/{transfer_id}/cancel", response_model=PartsTransferResponse)
def cancel_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE)),
):
    transfer = _load_transfer(db, transfer_id)
    if not transfer:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Передача не найдена"})
    if transfer.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail={"error": "STATUS_ERROR",
                                    "message": "Нельзя отменить проведённую передачу"})
    transfer.status = "cancelled"
    db.commit()
    transfer = _load_transfer(db, transfer.id)
    return _build_response(transfer, db)
