from sqlmodel import SQLModel
from decimal import Decimal 

class ProductCreate(SQLModel):
    name: str
    sku: str
    price: Decimal
    warehouse_id: int
    initial_quantity: int | None = 0
