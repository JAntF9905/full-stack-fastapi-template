from typing import Optional

from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select

# Assuming your models are in a file named models.py
# from .models import SearchResultFood, AbridgedFoodNutrient, SearchResultFoodBase, AbridgedFoodNutrientBase

# For demonstration purposes, we'll redefine them here.
# In a real project, you would import them from your models.py file.

class AbridgedFoodNutrientBase(SQLModel):
    """Base model for Abridged Food Nutrient."""
    number: int | None = Field(default=None, index=True)
    name: str | None = Field(default=None, index=True)
    amount: float | None = None
    unitName: str | None = None
    derivationCode: str | None = None
    derivationDescription: str | None = None

class AbridgedFoodNutrient(AbridgedFoodNutrientBase, table=True):
    """SQLModel for Abridged Food Nutrient."""
    id: int | None = Field(default=None, primary_key=True)
    food_id: int | None = Field(default=None, foreign_key="searchresultfood.id")
    food: Optional["SearchResultFood"] = Relationship(back_populates="foodNutrients")

class SearchResultFoodBase(SQLModel):
    """Base model for Search Result Food."""
    fdcId: int = Field(index=True)
    dataType: str | None = None
    description: str = Field(index=True)
    foodCode: str | None = None
    publicationDate: str | None = None
    scientificName: str | None = None
    brandOwner: str | None = Field(default=None, index=True)
    gtinUpc: str | None = Field(default=None, index=True)
    ingredients: str | None = None
    ndbNumber: str | None = None
    additionalDescriptions: str | None = None
    allHighlightFields: str | None = None
    score: float | None = None

class SearchResultFood(SearchResultFoodBase, table=True):
    """SQLModel for Search Result Food."""
    id: int | None = Field(default=None, primary_key=True)
    foodNutrients: list[AbridgedFoodNutrient] = Relationship(back_populates="food")

# --- Database Engine Setup ---
# You should replace this with your actual database connection string
# and engine creation from your main application file.
# For PostgreSQL, it would look something like:
# DATABASE_URL = "postgresql://user:password@host:port/database"
# engine = create_engine(DATABASE_URL)

# Placeholder engine for demonstration (using SQLite in memory)
# In a real app, use the engine created in your main file.
engine = create_engine("sqlite:///:memory:")

def create_db_and_tables():
    """Creates the database tables based on the SQLModel metadata."""
    SQLModel.metadata.create_all(engine)

# --- CRUD Operations ---

def create_food_item(food_data: SearchResultFoodBase) -> SearchResultFood:
    """
    Creates a new food item in the database.

    Args:
        food_data: The food data to create, based on SearchResultFoodBase.

    Returns:
        The created SearchResultFood object with its database ID.
    """
    with Session(engine) as session:
        # Create the SearchResultFood object from the base model
        db_food = SearchResultFood.model_validate(food_data) # Use model_validate for Pydantic v2+

        # If food_data includes nested nutrients, handle them
        # This assumes food_data might have a foodNutrients attribute
        if hasattr(food_data, 'foodNutrients') and food_data.foodNutrients:
             for nutrient_data in food_data.foodNutrients:
                 db_nutrient = AbridgedFoodNutrient.model_validate(nutrient_data)
                 db_food.foodNutrients.append(db_nutrient)


        session.add(db_food)
        session.commit()
        session.refresh(db_food)
        return db_food

def get_food_item_by_id(food_id: int) -> SearchResultFood | None:
    """
    Retrieves a food item by its database ID.

    Args:
        food_id: The database ID of the food item.

    Returns:
        The SearchResultFood object if found, otherwise None.
    """
    with Session(engine) as session:
        statement = select(SearchResultFood).where(SearchResultFood.id == food_id)
        results = session.exec(statement)
        food = results.first()
        return food

def get_all_food_items() -> list[SearchResultFood]:
    """
    Retrieves all food items from the database.

    Returns:
        A list of SearchResultFood objects.
    """
    with Session(engine) as session:
        statement = select(SearchResultFood)
        results = session.exec(statement)
        foods = results.all()
        return foods

def update_food_item(food_id: int, food_update_data: SearchResultFoodBase) -> SearchResultFood | None:
    """
    Updates an existing food item in the database.

    Args:
        food_id: The database ID of the food item to update.
        food_update_data: The updated food data.

    Returns:
        The updated SearchResultFood object if found and updated, otherwise None.
    """
    with Session(engine) as session:
        statement = select(SearchResultFood).where(SearchResultFood.id == food_id)
        results = session.exec(statement)
        db_food = results.first()

        if db_food:
            # Update fields from the update data
            for key, value in food_update_data.model_dump(exclude_unset=True).items(): # Use model_dump for Pydantic v2+
                if key != "foodNutrients": # Handle nested nutrients separately if needed
                     setattr(db_food, key, value)

            # Basic handling for updating nested nutrients (can be more complex depending on needs)
            # This example replaces the existing nutrients with the new ones provided
            if hasattr(food_update_data, 'foodNutrients') and food_update_data.foodNutrients is not None:
                 # Remove existing nutrients
                 for existing_nutrient in db_food.foodNutrients:
                     session.delete(existing_nutrient)
                 db_food.foodNutrients = [] # Clear the list

                 # Add new nutrients
                 for nutrient_data in food_update_data.foodNutrients:
                     db_nutrient = AbridgedFoodNutrient.model_validate(nutrient_data)
                     db_food.foodNutrients.append(db_nutrient)


            session.add(db_food)
            session.commit()
            session.refresh(db_food)
            return db_food
        return None

def delete_food_item(food_id: int) -> bool:
    """
    Deletes a food item from the database by its database ID.

    Args:
        food_id: The database ID of the food item to delete.

    Returns:
        True if the food item was found and deleted, False otherwise.
    """
    with Session(engine) as session:
        statement = select(SearchResultFood).where(SearchResultFood.id == food_id)
        results = session.exec(statement)
        db_food = results.first()

        if db_food:
            session.delete(db_food)
            session.commit()
            return True
        return False

# Example Usage (requires database setup and table creation)
# if __name__ == "__main__":
#     create_db_and_tables()
#
#     # Create a new food item
#     new_food_data = SearchResultFoodBase(
#         fdcId=12345,
#         description="Sample Food Item",
#         dataType="Branded",
#         brandOwner="Sample Brand",
#         foodNutrients=[
#             AbridgedFoodNutrientBase(number=203, name="Protein", amount=10.0, unitName="g"),
#             AbridgedFoodNutrientBase(number=204, name="Fat", amount=5.0, unitName="g")
#         ]
#     )
#     created_food = create_food_item(new_food_data)
#     print(f"Created Food: {created_food}")
#
#     # Read a food item
#     read_food = get_food_item_by_id(created_food.id)
#     print(f"Read Food: {read_food}")
#
#     # Update a food item
#     update_data = SearchResultFoodBase(
#          fdcId=12345, # fdcId is required in base model, but won't be updated if not in exclude_unset
#          description="Updated Sample Food Item",
#          foodNutrients=[ # Example of replacing nutrients
#             AbridgedFoodNutrientBase(number=205, name="Carbohydrates", amount=20.0, unitName="g")
#          ]
#     )
#     updated_food = update_food_item(created_food.id, update_data)
#     print(f"Updated Food: {updated_food}")
#
#     # Get all food items
#     all_foods = get_all_food_items()
#     print(f"All Foods: {all_foods}")
#
#     # Delete a food item
#     delete_success = delete_food_item(created_food.id)
#     print(f"Deleted Food (success): {delete_success}")
#
#     # Verify deletion
#     deleted_food = get_food_item_by_id(created_food.id)
#     print(f"Food after deletion: {deleted_food}")

