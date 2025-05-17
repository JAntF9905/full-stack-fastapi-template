import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

# from database import save_order, save_order_item
from utils import normalize_price, setup_logger
from dotenv import load_dotenv
from app.orders_model import Order
from sqlmodel import Session, SQLModel, create_engine
from datetime import datetime
from app.core.db import engine  # Use the shared DB engine

# Add the backend directory to the Python path so that "app" is resolved correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load environment variables from a .env file (ensure you have one at the root)
env_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
# ... existing code ...
print(env_file)
if not os.path.exists(env_file):
    print("Error: .env file not found. Exiting.")
    sys.exit(1)
load_dotenv(env_file)


class ExtractThinker:
    def __init__(self):
        self.logger = setup_logger()
        self.driver = self.setup_driver_headless()
        self.wait = WebDriverWait(self.driver, 10)

    def setup_driver_headless(self):
        """Initializes a headless Chrome WebDriver."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        self.logger.info("Headless WebDriver initialized.")
        return webdriver.Chrome(options=options)

    def log_info(self, message):
        try:
            page_title = self.driver.title
        except Exception as e:
            page_title = "Unknown Page"
            self.logger.warning("Unable to retrieve page title: %s", e)
        self.logger.info(f"[{page_title}] {message}")

    def generate_css_selector(self, element):
        selector = element.tag_name
        if element.get_attribute("id"):
            selector += f"#{element.get_attribute('id')}"
            return selector
        if element.get_attribute("class"):
            classes = ".".join(element.get_attribute("class").split())
            selector += f".{classes}"
        return selector

    def print_visible_css_selectors(self):
        try:
            self.log_info("Collecting all elements on the page...")
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, "*")
            self.log_info(f"Total elements found: {len(all_elements)}")
            visible_selectors = []
            for element in all_elements:
                if element.is_displayed():
                    selector = self.generate_css_selector(element)
                    visible_selectors.append(selector)
            self.log_info(f"Total visible elements: {len(visible_selectors)}")
            for selector in visible_selectors:
                print(selector)
        except Exception as e:
            self.logger.error(f"Error while printing visible CSS selectors: {e}")

    def login(self):
        username = os.getenv("CUB_USERNAME")
        password = os.getenv("CUB_PASSWORD")
        self.driver.get("https://www.cub.com")
        self.log_info("Opened Cub homepage.")
        time.sleep(3)
        try:
            modal = self.driver.find_elements(By.ID, "outside-modal")
            if modal:
                self.log_info("Closing modal...")
                ActionChains(self.driver).move_by_offset(10, 10).click().perform()
                time.sleep(2)
            self.log_info("Locating 'Sign In' button...")
            sign_in_button = self.driver.find_element(
                By.XPATH, "//button[contains(text(), 'Sign In')]"
            )
            self.driver.execute_script("arguments[0].click();", sign_in_button)
            self.log_info("Clicked 'Sign In' button.")
            time.sleep(3)
            username_input = self.driver.find_element(By.ID, "signInName")
            password_input = self.driver.find_element(By.ID, "password")
            print(username_input)
            username_input.send_keys(username)
            self.log_info("Entered username.")
            password_input.send_keys(password)
            self.log_info("Entered password.")
            submit_button = self.driver.find_element(
                By.XPATH, "//button[contains(text(), 'Continue')]"
            )
            self.driver.execute_script("arguments[0].click();", submit_button)
            self.log_info("Clicked 'Continue' button.")
            time.sleep(5)
            self.log_info("Checking login status...")
            account_button = self.driver.find_element(
                By.XPATH, "//button[@id='AccountHeaderButton']"
            )
            if "My Account" in account_button.text:
                self.log_info("Login successful!")
                return True
            else:
                self.log_info("Login failed!")
                return False
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def navigate_to_my_orders(self):
        try:
            self.log_info("Navigating to My Orders page...")
            account_button = self.driver.find_element(
                By.XPATH, "//button[@id='AccountHeaderButton']"
            )
            self.driver.execute_script("arguments[0].click();", account_button)
            self.log_info("Clicked on Account Button.")
            time.sleep(2)
            my_orders_link = self.wait.until(
                EC.presence_of_element_located((By.LINK_TEXT, "My Orders"))
            )
            my_orders_link.click()
            self.log_info("Clicked on 'My Orders' link.")
            time.sleep(5)
            soup = BeautifulSoup(
                self.driver.page_source, "html.parser", from_encoding="utf8"
            )
            order_sections = soup.find_all(
                "section",
                {"data-testid": lambda x: x and "order-card-info-testId" in x},
            )
            if not order_sections:
                self.logger.warning("No order sections found in the HTML.")
                return
            for idx, section in enumerate(order_sections, start=1):
                self.logger.info(f"\n--- Order {idx} ---")
                order_details = self.parse_order_list(section)
                if order_details is None:
                    self.logger.warning(
                        "Order details missing, skipping logging of order fields."
                    )
                    continue
                for key, value in order_details.items():
                    self.logger.info(f"{key}: {value}")
            orders_visited = 0
            while orders_visited < 3:
                orders_list = self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "ul[data-testid='orders-list-testId']")
                    )
                )
                self.log_info("Orders list loaded.")
                orders = orders_list.find_elements(By.TAG_NAME, "li")
                if orders_visited >= len(orders):
                    self.log_info("No more new orders to process.")
                    break
                order = orders[orders_visited]
                self.log_info(
                    f"Processing order {orders_visited + 1} of {len(orders)}."
                )
                self.navigate_to_order_details(order)
                time.sleep(3)
                self.parse_order_details()
                self.driver.back()
                self.log_info("Returned to My Orders page.")
                time.sleep(5)
                orders_visited += 1
        except Exception as e:
            self.logger.error(f"Error navigating orders: {e}")

    def navigate_to_order_details(self, order_element):
        try:
            order_link = order_element.find_element(By.TAG_NAME, "a")
            order_link.click()
            self.log_info("Navigated to order details page.")
        except Exception as e:
            self.logger.error(f"Error navigating to order details: {e}")
            raise

    def parse_order_list(self, section):
        """
        Parses a single order section and extracts relevant details.

        Args:
            section (bs4.element.Tag): The BeautifulSoup Tag object representing the order section.

        Returns:
            dict: A dictionary containing extracted order details.
        """
        order_details = {}
        # Define the locator strategies in order of preference
        locator_strategies = [
            (By.CSS_SELECTOR, "span[data-testid^='order-number-testId']"),
            # Using XPath starts-with() to match elements where data-testid begins with 'order-number-testId-'
            (By.XPATH, "//span[starts-with(@data-testid, 'order-number-testId-')]"),
        ]
        order_number_element = self.locate_element_with_fallback(locator_strategies)
        order_number_text = order_number_element.text
        self.logger.info(f"Retrieved order number: {order_number_text}")
        # Extract Date Placed
        date_placed_divs = [
            div
            for div in section.find_all("div")
            if div.has_attr("data-testid") and "placed" in div["data-testid"]
        ]
        if date_placed_divs:
            date_placed_text = date_placed_divs[0].contents[1].strip()
            order_details["date_placed"] = date_placed_text
            self.logger.info(f"Date Placed: {date_placed_text}")
        else:
            order_details["date_placed"] = "N/A"
            self.logger.warning("Date Placed div not found.")

        # Extract Activity Time
        action_time_divs = [
            div
            for div in section.find_all("div")
            if div.has_attr("data-testid") and "timeslot" in div["data-testid"]
        ]
        if action_time_divs:
            action_time_text = action_time_divs[0].get_text().strip()
            order_details["Activity Time"] = action_time_text
            self.logger.info(f"Activity Time: {action_time_text}")
        else:
            order_details["Activity Time"] = "N/A"
            self.logger.warning("Activity Time div not found.")

        # Extract Order Type Location and Determine Order Type
        order_type_location_divs = [
            div
            for div in section.find_all("div")
            if div.has_attr("data-testid") and "address" in div["data-testid"]
        ]
        if order_type_location_divs:
            # Determine order type based on the first word
            order_type_first_word = (
                order_type_location_divs[0].next.text.split(" ")[0].lower()
            )
            order_type = "delivery" if order_type_first_word == "delivery" else "pickup"
            order_details["order_type"] = order_type
            self.logger.info(f"Order Type: {order_type}")
            order_type_location = ""
            # Extract and clean Order Type Location
            for div in order_type_location_divs:
                text = div.get_text()
                if text.strip():  # Ignore empty text
                    order_type_location += (
                        text.strip()
                        .split("Location")[1]
                        .replace(" \n                  ", "")
                    )
                # print("Location:", order_type_location.strip())
            order_details["location"] = order_type_location
            self.logger.info(f"Order Type Location: {order_type_location}")
        else:
            order_details["location"] = "N/A"
            order_details["Order Type"] = "N/A"
            self.logger.warning("Order Type Location divs not found.")

        # Extract Items
        items_divs = [
            div
            for div in section.find_all("div")
            if div.has_attr("data-testid") and "count" in div["data-testid"]
        ]
        if items_divs:
            items_text = items_divs[0].get_text().replace("Items", "").strip()
            order_details["Items"] = items_text
            self.logger.info(f"Items: {items_text}")
        else:
            order_details["Items"] = "N/A"
            self.logger.warning("Items div not found.")

        # Extract Total (Estimated)
        total_divs = [
            div
            for div in section.find_all("div")
            if div.has_attr("data-testid") and "total" in div["data-testid"]
        ]
        if total_divs:
            total_estimated = total_divs[0].contents[1].strip()
            order_details["total_price"] = total_estimated
            self.logger.info(f"Total (Estimated): {total_estimated}")
        else:
            order_details["total_price"] = "0.00"
            self.logger.warning("Total div not found.")

        # Save the order details using our orders_crud.py
        from app.orders_crud import create_order
        from app.orders_model import Order
        from datetime import datetime, date

        try:
            date_placed = order_details.get("date_placed")
            # Convert to date if it's a string
            if isinstance(date_placed, str) and date_placed != "N/A":
                try:
                    order_date = datetime.strptime(date_placed, "%m/%d/%Y").date()
                except Exception:
                    order_date = date.today()
            elif isinstance(date_placed, date):
                order_date = date_placed
            else:
                order_date = date.today()
            order = Order(
                order_number=order_details.get("order_number_text", "N/A"),
                order_date=order_date,
                order_type=order_details.get("order_type", "delivery"),
                total_price=order_details.get("total_price", "0.00"),
            )
            with Session(engine) as session:
                create_order(session, order)
                self.logger.info(f"Order saved: {order.order_number}")
        except Exception as e:
            self.logger.error(f"Error saving order: {e}")

        return order_details

    # def parse_order_list(self, section):
    #     order_number = section.find("span", {"data-testid": "order-number"})
    #     date_placed = section.find("span", {"data-testid": "order-date"})
    #     order_type = section.find("span", {"data-testid": "order-type"})
    #     location = section.find("span", {"data-testid": "order-location"})
    #     total_price = section.find("span", {"data-testid": "order-total"})

    #     # Only proceed if order_number and date_placed are present
    #     if not order_number or not date_placed:
    #         self.logger.warning("Skipping order: missing order_number or order_date")
    #         return None

    #     order_data = {
    #         "order_number": order_number.text.strip(),
    #         "order_date": datetime.strptime(date_placed.text.strip(), "%m/%d/%Y"),
    #         "order_type": order_type.text.strip() if order_type else "delivery",
    #         "store": "Cub",
    #         "store_location": location.text.strip() if location else "N/A",
    #         "store_type": "Grocery",
    #         "total": float(total_price.text.replace("$", "").strip()) if total_price else 0.0,
    #     }

    #     order = Order(**order_data)
    #     try:
    #         with Session(engine) as session:
    #             from app.orders_crud import create_order
    #             create_order(session, order)
    #             self.logger.info(f"Order saved: {order.order_number}")
    #     except Exception as e:
    #         self.logger.error(f"Error saving order: {e}")

    #     return order_data

    def parse_order_details(self):
        try:
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(text(), 'Items Ordered')]")
                )
            )
            self.log_info("Items Ordered section loaded.")
            product_items = self.driver.find_elements(
                By.XPATH, "//div[contains(@data-testid, 'product-item-testId')]"
            )
            self.log_info(f"Found {len(product_items)} product items on the page.")
            from app.store_model import OrderItem

            with Session(engine) as session:
                for product in product_items:
                    try:
                        product_number = product.get_attribute("data-testid").split(
                            "-"
                        )[-1]
                        product_text = product.text.split("\n")
                        if len(product_text) >= 4:
                            name, quantity, price, total_cost = product_text[:4]
                            price = normalize_price(price)
                            total_cost = normalize_price(total_cost)
                            # You must provide valid values for order_id and product_id as required by your model.
                            # Here, order_id and product_id are set to None as placeholders; replace with actual IDs as needed.
                            order_item = OrderItem(
                                order_id=None,  # Replace with actual order ID if available
                                product_id=None,  # Replace with actual product ID if available
                                quantity=int(quantity) if quantity.isdigit() else 1,
                                unit_price=price,
                            )
                            session.add(order_item)
                            self.logger.info(
                                f"OrderItem saved: {name} - {quantity} - {price}"
                            )
                        else:
                            self.logger.warning(
                                f"Unexpected product text format: {product_text}"
                            )
                    except Exception as e:
                        self.logger.error(f"Error parsing product: {e}")
                session.commit()
        except TimeoutException:
            self.logger.error(
                "Failed to locate the order number element using all strategies."
            )
        except Exception as e:
            self.logger.error(f"Error in order parsing: {e}")

    def shutdown(self):
        self.driver.quit()
        self.logger.info("Browser closed.")

    def execute(self):
        if self.login():
            self.navigate_to_my_orders()
        else:
            self.logger.error("Login failed. Extraction aborted.")
        self.shutdown()


if __name__ == "__main__":
    scraper = ExtractThinker()
    scraper.execute()
