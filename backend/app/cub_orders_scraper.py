import os
import sys
import time

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import models and CRUD
from sqlmodel import Session, create_engine
from store_crud import (
    create_order,
    create_store,
    get_order_by_order_number,
    get_store_by_id,
)
from store_models import OrderBase, StoreBase

# Load environment variables
env_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(env_file):
    load_dotenv(env_file)

# Database setup (replace with your actual DB URL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///cub_orders.db")
engine = create_engine(DATABASE_URL)

class CubOrderScraper:
    def __init__(self, headless=True):
        self.driver = self.setup_driver_headless(headless)
        self.wait = WebDriverWait(self.driver, 10)
        self.session = Session(engine)

    def setup_driver_headless(self, headless=True):
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        return webdriver.Chrome(options=options)

    def login(self):
        username = os.getenv("CUB_USERNAME")
        password = os.getenv("CUB_PASSWORD")
        self.driver.get("https://www.cub.com")
        time.sleep(3)
        try:
            modal = self.driver.find_elements(By.ID, "outside-modal")
            if modal:
                ActionChains(self.driver).move_by_offset(10, 10).click().perform()
                time.sleep(2)
            sign_in_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign In')]")
            self.driver.execute_script("arguments[0].click();", sign_in_button)
            time.sleep(3)
            username_input = self.driver.find_element(By.ID, "signInName")
            password_input = self.driver.find_element(By.ID, "password")
            username_input.send_keys(username)
            password_input.send_keys(password)
            submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
            self.driver.execute_script("arguments[0].click();", submit_button)
            time.sleep(5)
            account_button = self.driver.find_element(By.XPATH, "//button[@id='AccountHeaderButton']")
            if "My Account" in account_button.text:
                return True
            else:
                return False
        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def navigate_to_my_orders(self):
        try:
            account_button = self.driver.find_element(By.XPATH, "//button[@id='AccountHeaderButton']")
            self.driver.execute_script("arguments[0].click();", account_button)
            time.sleep(2)
            my_orders_link = self.wait.until(
                EC.presence_of_element_located((By.LINK_TEXT, "My Orders"))
            )
            my_orders_link.click()
            time.sleep(5)
            soup = BeautifulSoup(self.driver.page_source, "html.parser", from_encoding="utf8")
            order_sections = soup.find_all(
                "section",
                {"data-testid": lambda x: x and "order-card-info-testId" in x},
            )
            if not order_sections:
                print("No order sections found.")
                return
            for idx, section in enumerate(order_sections[:3], start=1):
                print(f"\n--- Order {idx} ---")
                order_details = self.parse_order_list(section)
                for key, value in order_details.items():
                    print(f"{key}: {value}")
        except Exception as e:
            print(f"Error navigating orders: {e}")

    def parse_order_list(self, section):
        order_details = {}
        # Order number
        order_number_span = section.find("span", {"data-testid": lambda x: x and x.startswith("order-number-testId")})
        order_number_text = order_number_span.text.strip() if order_number_span else "N/A"
        order_details["order_number"] = order_number_text
        # Date placed
        date_placed_div = section.find("div", {"data-testid": lambda x: x and "placed" in x})
        date_placed = date_placed_div.contents[1].strip() if date_placed_div and len(date_placed_div.contents) > 1 else "N/A"
        order_details["date_placed"] = date_placed
        # Order type/location
        order_type_div = section.find("div", {"data-testid": lambda x: x and "address" in x})
        order_type = "delivery" if order_type_div and order_type_div.text.lower().startswith("delivery") else "pickup"
        order_details["order_type"] = order_type
        location = order_type_div.text.strip() if order_type_div else "N/A"
        order_details["location"] = location
        # Items
        items_div = section.find("div", {"data-testid": lambda x: x and "count" in x})
        items = items_div.text.replace("Items", "").strip() if items_div else "N/A"
        order_details["items"] = items
        # Total price
        total_div = section.find("div", {"data-testid": lambda x: x and "total" in x})
        total_price = total_div.contents[1].strip() if total_div and len(total_div.contents) > 1 else "0.00"
        order_details["total_price"] = total_price
        # Save to DB using store_crud
        store = get_store_by_id(session=self.session, store_id=1)
        if not store:
            store_base = StoreBase(name="Cub", location=order_details["location"], store_type="Grocery")
            store = create_store(session=self.session, store_create=store_base)
        order_base = OrderBase(
            store_id=store.id,
            order_number=order_number_text,
            order_date=date_placed,
            total_price=total_price,
            order_type=order_type
        )
        order = get_order_by_order_number(session=self.session, order_number=order_number_text)
        if not order:
            order = create_order(session=self.session, order_create=order_base)
        # Optionally, parse and save order items here
        return order_details

    def shutdown(self):
        self.driver.quit()
        self.session.close()
        print("Browser closed and DB session closed.")

    def execute(self):
        if self.login():
            self.navigate_to_my_orders()
        else:
            print("Login failed. Extraction aborted.")
        self.shutdown()

if __name__ == "__main__":
    # Set headless=False to see the browser window
    scraper = CubOrderScraper(headless=False)
    scraper.execute()
