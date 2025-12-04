from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ..Schemas.schemas import ProductCreate
from ..database.db import get_session, Product, Inventory, Warehouse
router = APIRouter()

@router.post("/products", status_code=201)
def create_product(payload: ProductCreate, session: Session = Depends(get_session)):

    #VALIDATE WAREHOUSE
    warehouse = session.get(Warehouse, payload.warehouse_id)
    if not warehouse:
        raise HTTPException(404, detail="Warehouse not found")

    #SKU UNIQUENESS
    sku_check = session.exec(select(Product).where(Product.sku == payload.sku)).first()
    if sku_check:
        raise HTTPException(409, detail="SKU already exists")

    #PRICE VALIDATION
    if payload.price < 0:
        raise HTTPException(400, detail="Price cannot be negative")

    #QUANTITY VALIDATION
    qty = payload.initial_quantity or 0
    if qty < 0:
        raise HTTPException(400, detail="Initial quantity cannot be negative")

    #TRANSACTION
    try:
        # Start transaction (SQLModel uses same Session semantics as SQLAlchemy)
        product = Product(
            name=payload.name,
            sku=payload.sku,
            price=payload.price
        )

        session.add(product)
        session.commit()
        session.refresh(product)

        # Create inventory record
        inventory = Inventory(
            product_id=product.id,
            warehouse_id=payload.warehouse_id,
            quantity=qty
        )

        session.add(inventory)
        session.commit()
        session.refresh(inventory)

        return {
            "message": "Product created successfully",
            "product_id": product.id
        }

    except Exception as e:
        session.rollback()
        raise HTTPException(500, detail=f"Error creating product: {str(e)}")
