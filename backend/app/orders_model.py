from typing import List, Optional
from sqlmodel import SQLModel, Field, Relationship

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_name: str
    product_price: str
    product_quantity: str
    product_total: str
    upc: Optional[str] = None
    product_number: Optional[str] = None
    order_id: Optional[int] = Field(default=None, foreign_key="order.id")

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_number: str
    order_date: str
    total_price: str
    items: List[OrderItem] = Relationship(back_populates="order")

OrderItem.order = Relationship(back_populates="items") 