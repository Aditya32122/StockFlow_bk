from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from typing import List, Dict
from datetime import datetime, timedelta

from app.database.db import get_session, Product, Inventory, Warehouse, InventoryLog, SupplierProduct, Supplier

router = APIRouter()

# Example thresholds per product type 
DEFAULT_LOW_STOCK_THRESHOLD = 20
PRODUCT_TYPE_THRESHOLDS = {
    # "product_type": threshold
    "electronics": 10,
}

@router.get("/companies/{company_id}/alerts/low-stock")
def low_stock_alerts(company_id: int, session: Session = Depends(get_session)):

    # Get all products for the company
    products_stmt = select(Product).where(Product.company_id == company_id)
    products = session.exec(products_stmt).all()
    if not products:
        raise HTTPException(status_code=404, detail="Company has no products")

    alerts = []

    for product in products:
        # Determine threshold for this product
        threshold = PRODUCT_TYPE_THRESHOLDS.get(getattr(product, "type", None), DEFAULT_LOW_STOCK_THRESHOLD)

        # Get inventories for this product across warehouses
        inv_stmt = select(Inventory, Warehouse).where(
            Inventory.product_id == product.id
        ).join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        results = session.exec(inv_stmt).all()

        for inventory, warehouse in results:
            # Skip if stock above threshold
            if inventory.quantity > threshold:
                continue

            #Check for recent sales activity (last 30 days)
            recent_sales_stmt = select(func.count(InventoryLog.id)).where(
                InventoryLog.inventory_id == inventory.id,
                InventoryLog.change_amount < 0,  # negative means sale
                InventoryLog.created_at >= datetime.utcnow() - timedelta(days=30)
            )
            recent_sales = session.exec(recent_sales_stmt).one()

            if recent_sales == 0:
                continue  # skip if no recent sales

            #Get supplier info (first supplier for product)
            supplier_stmt = select(Supplier).join(SupplierProduct).where(
                SupplierProduct.product_id == product.id
            )
            supplier = session.exec(supplier_stmt).first()

            supplier_info = None
            if supplier:
                supplier_info = {
                    "id": supplier.id,
                    "name": supplier.name,
                    "contact_email": supplier.contact_email
                }

            #Estimate days until stockout (simple avg daily sales over 30 days)
            sales_qty_stmt = select(func.sum(InventoryLog.change_amount)).where(
                InventoryLog.inventory_id == inventory.id,
                InventoryLog.change_amount < 0,
                InventoryLog.created_at >= datetime.utcnow() - timedelta(days=30)
            )
            total_sold = session.exec(sales_qty_stmt).one() or 0
            avg_daily_sales = abs(total_sold) / 30 if total_sold else 0
            days_until_stockout = int(inventory.quantity / avg_daily_sales) if avg_daily_sales > 0 else None

            alerts.append({
                "product_id": product.id,
                "product_name": product.name,
                "sku": product.sku,
                "warehouse_id": warehouse.id,
                "warehouse_name": warehouse.name,
                "current_stock": inventory.quantity,
                "threshold": threshold,
                "days_until_stockout": days_until_stockout,
                "supplier": supplier_info
            })

    return {
        "alerts": alerts,
        "total_alerts": len(alerts)
    }
