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
            sign_in_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign In')]")
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
            submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
            self.driver.execute_script("arguments[0].click();", submit_button)
            self.log_info("Clicked 'Continue' button.")
            time.sleep(5)
            self.log_info("Checking login status...")
            account_button = self.driver.find_element(By.XPATH, "//button[@id='AccountHeaderButton']")
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
            account_button = self.driver.find_element(By.XPATH, "//button[@id='AccountHeaderButton']")
            self.driver.execute_script("arguments[0].click();", account_button)
            self.log_info("Clicked on Account Button.")
            time.sleep(2)
            my_orders_link = self.wait.until(
                EC.presence_of_element_located((By.LINK_TEXT, "My Orders"))
            )
            my_orders_link.click()
            self.log_info("Clicked on 'My Orders' link.")
            time.sleep(5)
            soup = BeautifulSoup(self.driver.page_source, "html.parser", from_encoding="utf8")
            order_sections = soup.find_all("section", {"data-testid": lambda x: x and "order-card-info-testId" in x})
            if not order_sections:
                self.logger.warning("No order sections found in the HTML.")
                return
            for idx, section in enumerate(order_sections, start=1):
                self.logger.info(f"\n--- Order {idx} ---")
                order_details = self.parse_order_list(section)
                for key, value in order_details.items():
                    self.logger.info(f"{key}: {value}")
            orders_visited = 0
            while orders_visited < 3:
                orders_list = self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "ul[data-testid='orders-list-testId']")
                    )
                )
                orders = orders_list.find_elements(By.TAG_NAME, "li")
                if orders_visited >= len(orders):
                    self.log_info("No more new orders to process.")
                    break
                order = orders[orders_visited]
                self.log_info(f"Processing order {orders_visited + 1} of {len(orders)}.")
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


    def parse_my_orders(self):
        """Extracts order details from the My Orders page."""
        try:
            # Define the locator strategies in order of preference
            locator_strategies = [
                (By.CSS_SELECTOR, "span[data-testid^='order-number-testId']"),
                # Using XPath starts-with() to match elements where data-testid begins with 'order-number-testId-'
                (By.XPATH, "//span[starts-with(@data-testid, 'order-number-testId-')]")
            ]

            # Use the helper method to locate the element
            order_number_element = self.locate_element_with_fallback(locator_strategies)
            order_number_text = order_number_element.text
            # Extract order number (e.g., "6009553") from text "Order #6009553"
            order_number = order_number_text.split("Order #")[1].strip()
            self.log_info(f"Retrieved order number: {order_number}")
            # Find the <section> element with class order-number
            order_section = soup.find('section', class_='order-number')

            # Extract the text within the section
            order_data = order_section.get_text()

            print(order_data)
            # Use get_order_details to retrieve order details by passing the order number.
            order_number, order_date, total_price = self.get_order_details(order_number)
            self.log_info(f"Order Details: Number: {order_number}, Date: {order_date}, Total Price: {total_price}")
            # Wait for the Items Ordered section to load
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Items Ordered')]"))
            )
            self.log_info("Items Ordered section loaded.")

            # Locate all product items on the page
            product_items = self.driver.find_elements(
                By.XPATH, "//div[contains(@data-testid, 'product-item-testId')]"
            )
            self.log_info(f"Found {len(product_items)} product items on the page.")
            # Process each product item
            for product_item in product_items:
                # Extract product details
                product_name = product_item.find_element(By.CSS_SELECTOR, "div[data-testid='product-name']").text
                product_price = product_item.find_element(By.CSS_SELECTOR, "div[data-testid='product-price']").text
                product_quantity = product_item.find_element(By.CSS_SELECTOR, "div[data-testid='product-quantity']").text
                product_total = product_item.find_element(By.CSS_SELECTOR, "div[data-testid='product-total']").text
                # Save the product details
                save_product(product_name, product_price, product_quantity, product_total)
                self.log_info(f"Saved product: {product_name} - {product_price} - {product_quantity} - {product_total}")
            self.log_info("All product items processed.")
        except Exception as e:
            self.logger.error(f"Error in order parsing: {e}")
            raise


    # def parse_order_list(self, section):
    #     order_details = {}
    #     # Dummy parsing logic; replace with your actual parsing code.
    #     order_details["order_number_text"] = "12345"
    #     order_details["date_placed"] = "2025-01-01"
    #     order_details["order_type"] = "delivery"
    #     order_details["location"] = "Cub Location"
    #     order_details["Items"] = "3"
    #     order_details["total_price"] = "25.00"
    #     # try:
    #     #     save_order(
    #     #         order_number=order_details.get("order_number_text", "N/A"),
    #     #         order_date=order_details.get("date_placed", "N/A"),
    #     #         order_type=order_details.get("order_type", "delivery"),
    #     #         store="Cub",
    #     #         store_location=order_details.get("location", "N/A"),
    #     #         store_type="Grocery",
    #     #         total=order_details.get("total_price", "0.00"),
    #     #     )
    #     # except Exception as e:
    #     #     self.logger.error(f"Error saving order: {e}")
    #     return order_details

    def parse_order_details(self):
        try:
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Items Ordered')]"))
            )
            self.log_info("Items Ordered section loaded.")
            soup = BeautifulSoup(self.driver.page_source, "html.parser", from_encoding="utf8")
            product_items = self.driver.find_elements(By.XPATH, "//div[contains(@data-testid, 'product-item-testId')]")
            self.log_info(f"Found {len(product_items)} product items on the page.")
            for product in product_items:
                try:
                    product_number = product.get_attribute("data-testid").split("-")[-1]
                    upc = product_number
                    self.log_info(f"Product Number (UPC): {product_number}")
                    product_text = product.text.split("\n")
                    if len(product_text) >= 4:
                        name, quantity, price, total_cost = product_text[:4]
                        self.log_info(f"{name} - {quantity} - {price} - {total_cost}")
                        price = normalize_price(price)
                        total_cost = normalize_price(total_cost)
                        self.log_info(f"Normalized Price: {price}, Total Cost: {total_cost}")
                        # try:
                        #     save_order_item(
                        #         upc,
                        #         product_number,
                        #         name,
                        #         "12345",  # Dummy order number
                        #         price,
                        #         store="Cub",
                        #     )
                        # except Exception as e:
                        #     self.logger.error(f"Error saving order item: {e}")
                    else:
                        self.logger.warning(f"Unexpected product text format: {product_text}")
                except Exception as e:
                    self.logger.error(f"Error parsing product: {e}")
        except TimeoutException:
            self.logger.error("Failed to locate the order number element using all strategies.")
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
