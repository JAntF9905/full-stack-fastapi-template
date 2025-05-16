import os
import sys

# Add app directory to sys.path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../app"))

from food_crud import create_db_and_tables, create_food_item
from food_models import AbridgedFoodNutrientBase, SearchResultFoodBase

if __name__ == "__main__" or "pytest" in sys.modules:
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get("FDC_API_KEY", "")
else:
    from app.core.config import settings
    api_key = settings.FDC_API_KEY

import httpx

# Example UPC code (replace with the UPC you want to search)
upc_code = "735022007002"

# Allow UPC to be passed as a command-line argument
if len(sys.argv) > 1:
    upc_code = sys.argv[1]

# USDA FoodData Central search endpoint
url = "https://api.nal.usda.gov/fdc/v1/foods/search"

# Set up the parameters for the request
params = {"api_key": api_key, "query": upc_code}  # Using UPC code as the query

# Create tables (for demo/testing)
create_db_and_tables()

# Make the GET request
try:
    with httpx.Client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()  # Raises an exception for 4XX/5XX errors
        data = response.json()

    # Process the response
    if "foods" in data:
        for food in data["foods"]:
            # Convert food nutrients if present
            nutrients = [
                AbridgedFoodNutrientBase(**nutrient)
                for nutrient in food.get("foodNutrients", [])
            ]
            # Create food model
            food_data = SearchResultFoodBase(
                fdcId=food["fdcId"],
                dataType=food.get("dataType"),
                description=food.get("description"),
                foodCode=food.get("foodCode"),
                publicationDate=food.get("publicationDate"),
                scientificName=food.get("scientificName"),
                brandOwner=food.get("brandOwner"),
                gtinUpc=food.get("gtinUpc"),
                ingredients=food.get("ingredients"),
                ndbNumber=food.get("ndbNumber"),
                additionalDescriptions=food.get("additionalDescriptions"),
                allHighlightFields=food.get("allHighlightFields"),
                score=food.get("score"),
                foodNutrients=nutrients,
            )
            # Save to DB
            created = create_food_item(food_data)
            print(f"Saved to DB: {created}")
    else:
        print("No products found.")

except httpx.HTTPStatusError as exc:
    print(f"HTTP error occurred: {exc.response.status_code} - {exc.response.text}")
except httpx.RequestError as exc:
    print(f"An error occurred while requesting {exc.request.url!r}: {exc}")
