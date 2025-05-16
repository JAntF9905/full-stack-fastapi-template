from datetime import date, datetime
from decimal import Decimal  # Use Decimal for monetary values

from sqlmodel import Field, Relationship, SQLModel

# Define the base models for Pydantic compatibility

class StoreBase(SQLModel):
    """Base model for Store."""
    name: str = Field(index=True, max_length=255)
    location: str = Field(max_length=255)
    store_type: str = Field(max_length=50)

class ProductBase(SQLModel):
    """Base model for Product."""
    name: str = Field(index=True, max_length=255)
    category: str = Field(max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    unit_size: str | None = Field(default=None, max_length=50)
    upc_code: str | None = Field(default=None, unique=True, index=True, max_length=50)
    brand_type: str | None = Field(default=None, max_length=50) # "Store Brand" or "Commercial Brand"
    link: str | None = Field(default=None) # Text field can be represented as str

class ProductAvailabilityBase(SQLModel):
    """Base model for Product Availability."""
    store_id: int = Field(foreign_key="stores.id")
    product_id: int = Field(foreign_key="products.id")
    price: Decimal = Field(max_digits=10, decimal_places=2)
    # Use sa_column_kwargs to handle onupdate for datetime fields
    last_updated: datetime = Field(default_factory=datetime.utcnow,
                                    sa_column_kwargs={"onupdate": datetime.utcnow})

class OrderBase(SQLModel):
    """Base model for Order."""
    store_id: int = Field(foreign_key="stores.id")
    order_number: str = Field(unique=True, index=True, max_length=50)
    # Use default_factory for datetime.utcnow for default value
    order_date: date = Field(default_factory=date.today) # Changed to date as per original model
    total_price: Decimal = Field(max_digits=10, decimal_places=2)
    order_type: str | None = Field(default=None, max_length=50)

class OrderItemBase(SQLModel):
    """Base model for Order Item."""
    order_id: int = Field(foreign_key="orders.id")
    product_id: int = Field(foreign_key="products.id")
    quantity: int
    unit_price: Decimal = Field(max_digits=10, decimal_places=2)
    upc_code: str | None = Field(default=None, max_length=50)
    store_product_number: str | None = Field(default=None, max_length=50)
    store_product_name: str | None = Field(default=None, max_length=255)

class FoodItemBase(SQLModel):
    """Base model for Food Item."""
    fdc_id: str | None = Field(default=None, unique=True, index=True, max_length=50)
    name: str = Field(index=True, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    unit_size: str | None = Field(default=None, max_length=50)
    upc_code: str | None = Field(default=None, unique=True, index=True, max_length=50)
    brand_type: str | None = Field(default=None, max_length=50) # "Store Brand" or "Commercial Brand"
    link: str | None = Field(default=None) # Text field can be represented as str
    last_updated: datetime = Field(default_factory=datetime.utcnow,
                                    sa_column_kwargs={"onupdate": datetime.utcnow})

class PriceHistoryBase(SQLModel):
    """Base model for Price History."""
    food_item_id: int = Field(foreign_key="food_items.id")
    store_id: int = Field(foreign_key="stores.id")
    price: Decimal = Field(max_digits=10, decimal_places=2)
    discount_price: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    price_date: date = Field(default_factory=date.today) # Renamed from 'date' to 'price_date'
    unit_price: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    source: str = Field(max_length=50) # "in-store", "online", "store-pickup", "delivered"


# Define the SQLModel classes with table=True and relationships

class Store(StoreBase, table=True):
    """SQLModel for Store."""
    __tablename__ = "stores" # Explicitly define table name if different from class name
    id: int | None = Field(default=None, primary_key=True)

    # Relationships
    prices: list["PriceHistory"] = Relationship(back_populates="store")
    promotions: list["Promotion"] = Relationship(back_populates="store") # Assuming a Promotion model exists
    purchases: list["PersonalPurchase"] = Relationship(back_populates="store") # Assuming a PersonalPurchase model exists
    products_availability: list["ProductAvailability"] = Relationship(back_populates="store")
    orders: list["Order"] = Relationship(back_populates="store")


class Product(ProductBase, table=True):
    """SQLModel for Product."""
    __tablename__ = "products"
    id: int | None = Field(default=None, primary_key=True)

    # Relationships
    prices: list["PriceHistory"] = Relationship(back_populates="product") # Note: This relationship name conflicts with FoodItem.prices, might need clarification or renaming depending on your schema
    purchases: list["PersonalPurchase"] = Relationship(back_populates="product") # Assuming PersonalPurchase exists
    promotions: list["Promotion"] = Relationship(back_populates="product") # Assuming Promotion exists
    availability: list["ProductAvailability"] = Relationship(back_populates="product")
    order_items: list["OrderItem"] = Relationship(back_populates="product")


class ProductAvailability(ProductAvailabilityBase, table=True):
    """SQLModel for Product Availability."""
    __tablename__ = "product_availability"
    id: int | None = Field(default=None, primary_key=True)

    # Relationships
    store: "Store" = Relationship(back_populates="products_availability")
    product: "Product" = Relationship(back_populates="availability")


class Order(OrderBase, table=True):
    """SQLModel for Order."""
    __tablename__ = "orders"
    id: int | None = Field(default=None, primary_key=True)

    # Relationships
    store: "Store" = Relationship(back_populates="orders")
    items: list["OrderItem"] = Relationship(back_populates="order")


class OrderItem(OrderItemBase, table=True):
    """SQLModel for Order Item."""
    __tablename__ = "order_items"
    id: int | None = Field(default=None, primary_key=True)

    # Relationships
    order: "Order" = Relationship(back_populates="items")
    product: "Product" = Relationship(back_populates="order_items")


class FoodItem(FoodItemBase, table=True):
    """SQLModel for Food Item."""
    __tablename__ = "food_items"
    id: int | None = Field(default=None, primary_key=True)

    # Relationships
    prices: list["PriceHistory"] = Relationship(back_populates="food_item")


class PriceHistory(PriceHistoryBase, table=True):
    """SQLModel for Price History."""
    __tablename__ = "price_history"
    id: int | None = Field(default=None, primary_key=True)

    # Relationships
    food_item: "FoodItem" = Relationship(back_populates="prices")
    store: "Store" = Relationship(back_populates="prices")


# You would also need to define the 'Promotion' and 'PersonalPurchase'
# models if they exist in your application, similar to the above examples.
# For example:
# class PromotionBase(SQLModel):
#     ...
#
# class Promotion(PromotionBase, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     store_id: int = Field(foreign_key="stores.id")
#     product_id: int = Field(foreign_key="products.id")
#     store: "Store" = Relationship(back_populates="promotions")
#     product: "Product" = Relationship(back_populates="promotions")
#
# class PersonalPurchaseBase(SQLModel):
#     ...
#
# class PersonalPurchase(PersonalPurchaseBase, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     store_id: int = Field(foreign_key="stores.id")
#     product_id: int = Field(foreign_key="products.id")
#     store: "Store" = Relationship(back_populates="purchases")
#     product: "Product" = Relationship(back_populates="purchases")

# --- Database Engine Setup Example (in your main app file) ---
# You would typically create the engine in your main application file (e.g., main.py)
# and pass it to your dependencies.
#
# from sqlmodel import create_engine
# import os # You might use environment variables for connection details
#
# # Example PostgreSQL connection URL
# # Replace with your actual database credentials and host
# # DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@host:port/database")
#
# # For a local PostgreSQL instance with default user/db (replace if needed)
# # DATABASE_URL = "postgresql://postgres:password@localhost/mydatabase"
#
# # engine = create_engine(DATABASE_URL)
#
# def create_db_and_tables():
#     """Creates the database tables based on the SQLModel metadata."""
#     # Make sure your engine is created before calling this
#     # SQLModel.metadata.create_all(engine)
#     pass # Placeholder if engine is created elsewhere

