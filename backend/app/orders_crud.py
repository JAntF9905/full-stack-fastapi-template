from typing import List, Optional
from sqlmodel import Session, select
from .orders_model import Order, OrderItem

def create_order(session: Session, order: Order) -> Order:
    session.add(order)
    session.commit()
    session.refresh(order)
    return order

def get_order(session: Session, order_id: int) -> Optional[Order]:
    return session.get(Order, order_id)

def get_orders(session: Session) -> List[Order]:
    statement = select(Order)
    results = session.exec(statement)
    return list(results.all())

def delete_order(session: Session, order_id: int) -> bool:
    order = session.get(Order, order_id)
    if order:
        session.delete(order)
        session.commit()
        return True
    return False

def update_order(session: Session, order_id: int, order_data: dict) -> Optional[Order]:
    order = session.get(Order, order_id)
    if not order:
        return None
    for key, value in order_data.items():
        if hasattr(order, key):
            setattr(order, key, value)
    session.add(order)
    session.commit()
    session.refresh(order)
    return order