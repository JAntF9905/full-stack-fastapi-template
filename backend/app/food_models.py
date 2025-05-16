from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


# Define the model for AbridgedFoodNutrient, which is nested within SearchResultFood
class AbridgedFoodNutrientBase(SQLModel):
    """Base model for Abridged Food Nutrient."""
    number: int | None = Field(default=None, index=True) # Nutritional information number
    name: str | None = Field(default=None, index=True) # Name of the nutrient
    amount: float | None = None # Amount of the nutrient
    unitName: str | None = None # Unit of measurement for the nutrient
    derivationCode: str | None = None # Code for the derivation of the nutrient value
    derivationDescription: str | None = None # Description of how the nutrient value was derived

class AbridgedFoodNutrient(AbridgedFoodNutrientBase, table=True):
    """SQLModel for Abridged Food Nutrient."""
    id: int | None = Field(default=None, primary_key=True) # Primary key

    # Define the foreign key relationship back to SearchResultFood
    food_id: int | None = Field(default=None, foreign_key="searchresultfood.id")
    food: Optional["SearchResultFood"] = Relationship(back_populates="foodNutrients")


# Define the main model for SearchResultFood
class SearchResultFoodBase(SQLModel):
    """Base model for Search Result Food."""
    fdcId: int = Field(index=True) # Unique ID of the food (required)
    dataType: str | None = None # The type of the food data
    description: str = Field(index=True) # The description of the food (required)
    foodCode: str | None = None # Unique ID within FNDDS
    publicationDate: str | None = None # Date the item was published
    scientificName: str | None = None # The scientific name of the food
    brandOwner: str | None = Field(default=None, index=True) # Brand owner (for Branded Foods)
    gtinUpc: str | None = Field(default=None, index=True) # GTIN or UPC code (for Branded Foods)
    ingredients: str | None = None # List of ingredients (for Branded Foods)
    ndbNumber: str | None = None # Unique number for foundation foods (Foundation and SRLegacy)
    additionalDescriptions: str | None = None # Any additional descriptions
    allHighlightFields: str | None = None # All highlight fields
    score: float | None = None # Relative score indicating search match

class SearchResultFood(SearchResultFoodBase, table=True):
    """SQLModel for Search Result Food."""
    id: int | None = Field(default=None, primary_key=True) # Primary key for the database table

    # Define the relationship to AbridgedFoodNutrient
    foodNutrients: list[AbridgedFoodNutrient] = Relationship(back_populates="food")

# Example of how you might create tables (usually done in your main app file)
# from sqlmodel import create_engine
#
# # For SQLite:
# # engine = create_engine("sqlite:///database.db")
#
# # For PostgreSQL:
# # DATABASE_URL = "postgresql://user:password@host:port/database"
# # engine = create_engine(DATABASE_URL)
#
# def create_db_and_tables():
#     SQLModel.metadata.create_all(engine)

# To use these models:
# from sqlmodel import Session, select
# from .models import SearchResultFood, AbridgedFoodNutrient, engine
#
# def create_food_item(food_data: SearchResultFoodBase):
#     with Session(engine) as session:
#         db_food = SearchResultFood.from_orm(food_data)
#         session.add(db_food)
#         session.commit()
#         session.refresh(db_food)
#         return db_food
#
# def get_food_items():
#     with Session(engine) as session:
#         foods = session.exec(select(SearchResultFood)).all()
#         return foods

