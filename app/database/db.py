from sqlmodel import create_engine, SQLModel, Session, Field, Relationship
from decimal import Decimal
import os
from dotenv import load_dotenv
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, DECIMAL,UniqueConstraint

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

connection_string = DATABASE_URL
# engine is one for whole application
engine = create_engine(
    connection_string,
    connect_args={"sslmode": "require"},
    pool_recycle=300,
    pool_size=10,
    echo=True,
)

def get_session():
    with Session(engine) as session:
        yield session

# Company
class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, nullable=False, unique=True)
    address: Optional[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    warehouses: List["Warehouse"] = Relationship(back_populates="company")
    products: List["Product"] = Relationship(back_populates="company")
    suppliers: List["Supplier"] = Relationship(back_populates="company")

# Warehouse
class Warehouse(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", nullable=False)
    name: str = Field(nullable=False)
    location: Optional[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    company: Company = Relationship(back_populates="warehouses")
    inventory: List["Inventory"] = Relationship(back_populates="warehouse")

    __table_args__ = (
        UniqueConstraint('company_id', 'name', name='uq_warehouse_name_per_company'),
    )

# Product
class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", nullable=False)
    name: str = Field(nullable=False)
    sku: str = Field(nullable=False, index=True)
    price: Decimal = Field(sa_column=Column(DECIMAL(10, 2)))
    is_bundle: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    company: Company = Relationship(back_populates="products")
    inventory: List["Inventory"] = Relationship(back_populates="product")
    bundles: List["ProductBundle"] = Relationship(
        back_populates="parent_product", sa_relationship_kwargs={"primaryjoin": "Product.id==ProductBundle.parent_product_id"}
    )
    bundle_components: List["ProductBundle"] = Relationship(
        back_populates="child_product", sa_relationship_kwargs={"primaryjoin": "Product.id==ProductBundle.child_product_id"}
    )

    __table_args__ = (
        UniqueConstraint('company_id', 'sku', name='uq_product_sku_per_company'),
    )

# Inventory (product - warehouse)
class Inventory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", nullable=False)
    warehouse_id: int = Field(foreign_key="warehouse.id", nullable=False)
    quantity: int = Field(default=0)

    product: Product = Relationship(back_populates="inventory")
    warehouse: Warehouse = Relationship(back_populates="inventory")
    logs: List["InventoryLog"] = Relationship(back_populates="inventory")

    __table_args__ = (
        UniqueConstraint('product_id', 'warehouse_id', name='uq_inventory_product_warehouse'),
    )

# Inventory Logs
class InventoryLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    inventory_id: int = Field(foreign_key="inventory.id", nullable=False)
    change_amount: int
    previous_qty: int
    new_qty: int
    reason: Optional[str]
    changed_by: Optional[int]  # Could reference a user table
    created_at: datetime = Field(default_factory=datetime.utcnow)

    inventory: Inventory = Relationship(back_populates="logs")


# Supplier
class Supplier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", nullable=False)
    name: str = Field(nullable=False)
    contact_email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    company: Company = Relationship(back_populates="suppliers")
    supplier_products: List["SupplierProduct"] = Relationship(back_populates="supplier")


# Supplier - Product
class SupplierProduct(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    supplier_id: int = Field(foreign_key="supplier.id", nullable=False)
    product_id: int = Field(foreign_key="product.id", nullable=False)
    cost_price: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 2)))
    lead_time_days: Optional[int]

    supplier: Supplier = Relationship(back_populates="supplier_products")
    product: Product = Relationship()


# Product Bundles (self-referential)
class ProductBundle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    parent_product_id: int = Field(foreign_key="product.id", nullable=False)
    child_product_id: int = Field(foreign_key="product.id", nullable=False)
    quantity_required: int = Field(default=1)

    parent_product: Product = Relationship(back_populates="bundles", sa_relationship_kwargs={"foreign_keys": "[ProductBundle.parent_product_id]"})
    child_product: Product = Relationship(back_populates="bundle_components", sa_relationship_kwargs={"foreign_keys": "[ProductBundle.child_product_id]"})
