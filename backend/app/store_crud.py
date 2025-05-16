from sqlmodel import (
    Session,
    create_engine,
    select,
)

# Import all models from store_models.py
from .store_models import (
    FoodItem,
    FoodItemBase,
    Order,
    OrderBase,
    OrderItem,
    OrderItemBase,
    PriceHistory,
    PriceHistoryBase,
    # Promotion, PersonalPurchase  # Uncomment if/when these are defined
    Product,
    ProductAvailability,
    ProductAvailabilityBase,
    ProductBase,
    Store,
    StoreBase,
)

# --- Database Engine Setup ---
# You should replace this with your actual database connection string
# and engine creation from your main application file.
# For PostgreSQL, it would look something like:
# DATABASE_URL = "postgresql://user:password@host:port/database"
# engine = create_engine(DATABASE_URL)

# Placeholder engine for demonstration (using SQLite in memory)
# In a real app, use the engine created in your main file.
# For PostgreSQL, you would use your configured engine here:
# from your_app.database import engine # Example import
engine = create_engine("sqlite:///:memory:")  # Keeping placeholder for runnable example


def create_db_and_tables():
    """Creates the database tables based on the SQLModel metadata."""
    # Make sure your engine is created before calling this function
    # SQLModel.metadata.create_all(engine)
    pass  # Placeholder if engine is created elsewhere


# --- CRUD Operations for Store ---


def create_store(*, session: Session, store_create: StoreBase) -> Store:
    """Creates a new store."""
    db_store = Store.model_validate(store_create)
    session.add(db_store)
    session.commit()
    session.refresh(db_store)
    return db_store


def get_store_by_id(*, session: Session, store_id: int) -> Store | None:
    """Retrieves a store by its ID."""
    statement = select(Store).where(Store.id == store_id)
    return session.exec(statement).first()


def get_all_stores(*, session: Session) -> list[Store]:
    """Retrieves all stores."""
    statement = select(Store)
    return session.exec(statement).all()


def update_store(
    *, session: Session, db_store: Store, store_update: StoreBase
) -> Store:
    """Updates an existing store."""
    store_data = store_update.model_dump(exclude_unset=True)
    db_store.sqlmodel_update(store_data)
    session.add(db_store)
    session.commit()
    session.refresh(db_store)
    return db_store


def delete_store(*, session: Session, store_id: int) -> bool:
    """Deletes a store by its ID."""
    store = get_store_by_id(session=session, store_id=store_id)
    if store:
        session.delete(store)
        session.commit()
        return True
    return False


# --- CRUD Operations for Product ---


def create_product(*, session: Session, product_create: ProductBase) -> Product:
    """Creates a new product."""
    db_product = Product.model_validate(product_create)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product


def get_product_by_id(*, session: Session, product_id: int) -> Product | None:
    """Retrieves a product by its ID."""
    statement = select(Product).where(Product.id == product_id)
    return session.exec(statement).first()


def get_all_products(*, session: Session) -> list[Product]:
    """Retrieves all products."""
    statement = select(Product)
    return session.exec(statement).all()


def update_product(
    *, session: Session, db_product: Product, product_update: ProductBase
) -> Product:
    """Updates an existing product."""
    product_data = product_update.model_dump(exclude_unset=True)
    db_product.sqlmodel_update(product_data)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product


def delete_product(*, session: Session, product_id: int) -> bool:
    """Deletes a product by its ID."""
    product = get_product_by_id(session=session, product_id=product_id)
    if product:
        session.delete(product)
        session.commit()
        return True
    return False


# --- CRUD Operations for ProductAvailability ---


def create_product_availability(
    *, session: Session, pa_create: ProductAvailabilityBase
) -> ProductAvailability:
    """Creates a new product availability entry."""
    db_pa = ProductAvailability.model_validate(pa_create)
    session.add(db_pa)
    session.commit()
    session.refresh(db_pa)
    return db_pa


def get_product_availability_by_id(
    *, session: Session, pa_id: int
) -> ProductAvailability | None:
    """Retrieves a product availability entry by its ID."""
    statement = select(ProductAvailability).where(ProductAvailability.id == pa_id)
    return session.exec(statement).first()


def get_product_availability_for_store_product(
    *, session: Session, store_id: int, product_id: int
) -> ProductAvailability | None:
    """Retrieves product availability for a specific store and product."""
    statement = select(ProductAvailability).where(
        ProductAvailability.store_id == store_id,
        ProductAvailability.product_id == product_id,
    )
    return session.exec(statement).first()


def get_all_product_availability(*, session: Session) -> list[ProductAvailability]:
    """Retrieves all product availability entries."""
    statement = select(ProductAvailability)
    return session.exec(statement).all()


def update_product_availability(
    *, session: Session, db_pa: ProductAvailability, pa_update: ProductAvailabilityBase
) -> ProductAvailability:
    """Updates an existing product availability entry."""
    pa_data = pa_update.model_dump(exclude_unset=True)
    db_pa.sqlmodel_update(pa_data)
    session.add(db_pa)
    session.commit()
    session.refresh(db_pa)
    return db_pa


def delete_product_availability(*, session: Session, pa_id: int) -> bool:
    """Deletes a product availability entry by its ID."""
    pa = get_product_availability_by_id(session=session, pa_id=pa_id)
    if pa:
        session.delete(pa)
        session.commit()
        return True
    return False


# --- CRUD Operations for Order ---


def create_order(*, session: Session, order_create: OrderBase) -> Order:
    """Creates a new order."""
    db_order = Order.model_validate(order_create)
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    return db_order


def get_order_by_id(*, session: Session, order_id: int) -> Order | None:
    """Retrieves an order by its ID."""
    statement = select(Order).where(Order.id == order_id)
    return session.exec(statement).first()


def get_order_by_order_number(*, session: Session, order_number: str) -> Order | None:
    """Retrieves an order by its order number."""
    statement = select(Order).where(Order.order_number == order_number)
    return session.exec(statement).first()


def get_all_orders(*, session: Session) -> list[Order]:
    """Retrieves all orders."""
    statement = select(Order)
    return session.exec(statement).all()


def update_order(
    *, session: Session, db_order: Order, order_update: OrderBase
) -> Order:
    """Updates an existing order."""
    order_data = order_update.model_dump(exclude_unset=True)
    db_order.sqlmodel_update(order_data)
    session.add(db_order)
    session.commit()
    session.refresh(db_order)
    return db_order


def delete_order(*, session: Session, order_id: int) -> bool:
    """Deletes an order by its ID."""
    order = get_order_by_id(session=session, order_id=order_id)
    if order:
        session.delete(order)
        session.commit()
        return True
    return False


# --- CRUD Operations for OrderItem ---


def create_order_item(
    *, session: Session, order_item_create: OrderItemBase
) -> OrderItem:
    """Creates a new order item."""
    db_order_item = OrderItem.model_validate(order_item_create)
    session.add(db_order_item)
    session.commit()
    session.refresh(db_order_item)
    return db_order_item


def get_order_item_by_id(*, session: Session, order_item_id: int) -> OrderItem | None:
    """Retrieves an order item by its ID."""
    statement = select(OrderItem).where(OrderItem.id == order_item_id)
    return session.exec(statement).first()


def get_order_items_for_order(*, session: Session, order_id: int) -> list[OrderItem]:
    """Retrieves all order items for a specific order."""
    statement = select(OrderItem).where(OrderItem.order_id == order_id)
    return session.exec(statement).all()


def get_all_order_items(*, session: Session) -> list[OrderItem]:
    """Retrieves all order items."""
    statement = select(OrderItem)
    return session.exec(statement).all()


def update_order_item(
    *, session: Session, db_order_item: OrderItem, order_item_update: OrderItemBase
) -> OrderItem:
    """Updates an existing order item."""
    order_item_data = order_item_update.model_dump(exclude_unset=True)
    db_order_item.sqlmodel_update(order_item_data)
    session.add(db_order_item)
    session.commit()
    session.refresh(db_order_item)
    return db_order_item


def delete_order_item(*, session: Session, order_item_id: int) -> bool:
    """Deletes an order item by its ID."""
    order_item = get_order_item_by_id(session=session, order_item_id=order_item_id)
    if order_item:
        session.delete(order_item)
        session.commit()
        return True
    return False


# --- CRUD Operations for FoodItem ---


def create_food_item(*, session: Session, food_item_create: FoodItemBase) -> FoodItem:
    """Creates a new food item."""
    db_food_item = FoodItem.model_validate(food_item_create)
    session.add(db_food_item)
    session.commit()
    session.refresh(db_food_item)
    return db_food_item


def get_food_item_by_id(*, session: Session, food_item_id: int) -> FoodItem | None:
    """Retrieves a food item by its ID."""
    statement = select(FoodItem).where(FoodItem.id == food_item_id)
    return session.exec(statement).first()


def get_food_item_by_fdc_id(*, session: Session, fdc_id: str) -> FoodItem | None:
    """Retrieves a food item by its FDC ID."""
    statement = select(FoodItem).where(FoodItem.fdc_id == fdc_id)
    return session.exec(statement).first()


def get_food_item_by_upc_code(*, session: Session, upc_code: str) -> FoodItem | None:
    """Retrieves a food item by its UPC code."""
    statement = select(FoodItem).where(FoodItem.upc_code == upc_code)
    return session.exec(statement).first()


def get_all_food_items(*, session: Session) -> list[FoodItem]:
    """Retrieves all food items."""
    statement = select(FoodItem)
    return session.exec(statement).all()


def update_food_item(
    *, session: Session, db_food_item: FoodItem, food_item_update: FoodItemBase
) -> FoodItem:
    """Updates an existing food item."""
    food_item_data = food_item_update.model_dump(exclude_unset=True)
    db_food_item.sqlmodel_update(food_item_data)
    session.add(db_food_item)
    session.commit()
    session.refresh(db_food_item)
    return db_food_item


def delete_food_item(*, session: Session, food_item_id: int) -> bool:
    """Deletes a food item by its ID."""
    food_item = get_food_item_by_id(session=session, food_item_id=food_item_id)
    if food_item:
        session.delete(food_item)
        session.commit()
        return True
    return False


# --- CRUD Operations for PriceHistory ---


def create_price_history(
    *, session: Session, price_history_create: PriceHistoryBase
) -> PriceHistory:
    """Creates a new price history entry."""
    db_price_history = PriceHistory.model_validate(price_history_create)
    session.add(db_price_history)
    session.commit()
    session.refresh(db_price_history)
    return db_price_history


def get_price_history_by_id(
    *, session: Session, price_history_id: int
) -> PriceHistory | None:
    """Retrieves a price history entry by its ID."""
    statement = select(PriceHistory).where(PriceHistory.id == price_history_id)
    return session.exec(statement).first()


def get_price_history_for_food_item_and_store(
    *, session: Session, food_item_id: int, store_id: int
) -> list[PriceHistory]:
    """Retrieves price history for a specific food item and store."""
    statement = select(PriceHistory).where(
        PriceHistory.food_item_id == food_item_id, PriceHistory.store_id == store_id
    )
    return session.exec(statement).all()


def get_all_price_history(*, session: Session) -> list[PriceHistory]:
    """Retrieves all price history entries."""
    statement = select(PriceHistory)
    return session.exec(statement).all()


def update_price_history(
    *,
    session: Session,
    db_price_history: PriceHistory,
    price_history_update: PriceHistoryBase,
) -> PriceHistory:
    """Updates an existing price history entry."""
    price_history_data = price_history_update.model_dump(exclude_unset=True)
    db_price_history.sqlmodel_update(price_history_data)
    session.add(db_price_history)
    session.commit()
    session.refresh(db_price_history)
    return db_price_history


def delete_price_history(*, session: Session, price_history_id: int) -> bool:
    """Deletes a price history entry by its ID."""
    price_history = get_price_history_by_id(
        session=session, price_history_id=price_history_id
    )
    if price_history:
        session.delete(price_history)
        session.commit()
        return True
    return False


# --- Example Usage (requires database setup and table creation) ---
# if __name__ == "__main__":
#     # In a real application, you would typically create the engine and tables
#     # in your main application file or a dedicated database module, and then
#     # import the engine here.
#
#     # Example of creating tables (if running this file directly for testing)
#     # try:
#     #     create_db_and_tables()
#     # except Exception as e:
#     #     print(f"Error creating tables: {e}")
#     #     print("Make sure your PostgreSQL database is running and accessible.")
#     #     print("Also ensure you have psycopg2-binary installed (`pip install psycopg2-binary`)")
#
#     # Example: Create a store
#     # new_store_data = StoreBase(name="Grocer Mart", location="123 Main St", store_type="Supermarket")
#     # with Session(engine) as session:
#     #     created_store = create_store(session=session, store_create=new_store_data)
#     #     print(f"Created Store: {created_store}")
#
#     # Example: Get all stores
#     # with Session(engine) as session:
#     #     all_stores = get_all_stores(session=session)
#     #     print(f"All Stores: {all_stores}")
#
#     # Add more example usage for other models...
