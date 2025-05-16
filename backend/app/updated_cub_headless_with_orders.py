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

# Add the backend directory to the Python path so that "app" is resolved correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Import your Flask application factory or app instance
from app import create_app
from services import save_product, save_order_item, save_order
from utils import normalize_price, setup_logger
from dotenv import load_dotenv


# Load your environment variables
env_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if not os.path.exists(env_file):
    print("Error: .env file not found. Exiting.")
    sys.exit(1)
load_dotenv(env_file)


class ExtractThinker:
    def __init__(self):
        # Initialize Flask app and push application context
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Initialize logger, driver, and wait within the app context
        self.logger = setup_logger()
        self.driver = self.setup_driver_headless()
        self.wait = WebDriverWait(self.driver, 10)

    def setup_driver_headless(self):
        """Initializes and returns a headless Chrome WebDriver instance."""
        options = Options()
        options.add_argument("--headless")  # Run Chrome in headless mode
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")  # Ensure adequate resolution
        self.logger.info("Headless WebDriver initialized.")
        return webdriver.Chrome(options=options)

    def log_info(self, message):
        """
        Logs an info message with the current page title.

        Args:
            message (str): The message to log.
        """
        try:
            page_title = self.driver.title
        except Exception as e:
            page_title = "Unknown Page"
            self.logger.warning("Unable to retrieve page title: %s", e)
        self.logger.info(f"[{page_title}] {message}")

    def generate_css_selector(self, element):
        """
        Generates a unique CSS selector for a given WebElement.

        Args:
            element (WebElement): The Selenium WebElement.

        Returns:
            str: A unique CSS selector string.
        """
        selector = element.tag_name
        if element.get_attribute("id"):
            selector += f"#{element.get_attribute('id')}"
            return selector
        if element.get_attribute("class"):
            classes = ".".join(element.get_attribute("class").split())
            selector += f".{classes}"
        return selector

    def print_visible_css_selectors(self):
        """
        Finds all visible elements on the current page and prints their CSS selectors.
        """
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
            self.logger.info("Visible CSS Selectors:")
            for selector in visible_selectors:
                print(selector)  # Or use self.logger.info(selector) to log them
        except Exception as e:
            self.logger.error(f"Error while printing visible CSS selectors: {e}")

    def login(self):
        """Perform login to the Cub site in headless mode."""
        username = os.getenv("CUB_USERNAME")
        password = os.getenv("CUB_PASSWORD")
        self.driver.get("https://www.cub.com")
        self.log_info("Opened Cub homepage.")
        time.sleep(3)

        # Example: find and click the "Sign In" button then complete login steps.
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

    def locate_element_with_fallback(self, strategies, timeout=10):
        """
        Attempts to locate an element using a list of locator strategies.

        Args:
            strategies (list of tuple): A list of locator strategies (By, selector).
            timeout (int): Maximum time to wait for the element.

        Returns:
            WebElement: The located element.

        Raises:
            TimeoutException: If the element is not found using any of the strategies.
        """
        for strategy in strategies:
            try:
                by, selector = strategy
                self.log_info(
                    f"Trying to locate element using {by} with selector '{selector}'"
                )
                element = self.wait.until(
                    EC.presence_of_element_located((by, selector))
                )
                self.log_info(f"Element found using {by}.")
                return element
            except TimeoutException:
                self.logger.warning(
                    f"Element not found using {by} with selector '{selector}'."
                )
        self.logger.error("Element not found using all provided strategies.")
        raise TimeoutException("Element not found using all provided strategies.")

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
            (By.XPATH, "//span[starts-with(@data-testid, 'order-number-testId-')]")
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

        # Save the order details
        save_order(
            order_number=order_details.get("order_number_text", "N/A"),
            order_date=order_details.get("date_placed", "N/A"),
            order_type=order_details.get("order_type", "delivery"),
            # delivery_time=order_details.get("Activity Time", "N/A"),
            # item_count=order_details.get("Items", "N/A"),
            store="Cub",
            store_location=order_details.get("location", "N/A"),
            store_type="Grocery",
            total=order_details.get("total_price", "0.00"),
        )

        return order_details

    def parse_order_details(self):
        """Extracts order details from the My Orders page."""
        try:
            # Define the locator strategies in order of preference
            locator_strategies = [
                (By.CSS_SELECTOR, "span[data-testid^='order-number-testId']"),
                (
                    By.XPATH,
                    "//span[@data-testid='order-number-testId-6009553']",
                ),  # Specific XPath
            ]

            # Use the helper method to locate the element
            order_number_element = self.locate_element_with_fallback(locator_strategies)
            order_number_text = order_number_element.text
            self.logger.info(f"Retrieved order number: {order_number_text}")

            # Wait for the Items Ordered section to load
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(text(), 'Items Ordered')]")
                )
            )
            self.logger.info("Items Ordered section loaded.")
            soup = BeautifulSoup(
                self.driver.page_source, "html.parser", from_encoding="utf8"
            )
            with open("order.html", mode="w", encoding="utf8") as code:
                code.write(str(soup.prettify()))
            # Locate all product items on the page
            product_items = self.driver.find_elements(
                By.XPATH, "//div[contains(@data-testid, 'product-item-testId')]"
            )
            self.logger.info(f"Found {len(product_items)} product items on the page.")
            for product in product_items:
                try:
                    product_number = product.get_attribute("data-testid").split("-")[-1]
                    # At Cub, use the product number as the UPC
                    upc = product_number
                    self.logger.info(f"Product Number (UPC): {product_number}")

                    product_text = product.text.split("\n")
                    # Expecting at least 4 parts: name, quantity, price, total_cost
                    if len(product_text) >= 4:
                        name, quantity, price, total_cost = product_text[:4]
                        self.logger.info(
                            f"{name} - {quantity} - {price} - {total_cost}"
                        )

                        price = normalize_price(price)
                        total_cost = normalize_price(total_cost)
                        self.logger.info(
                            f"Normalized Price: {price}, Total Cost: {total_cost}"
                        )
                        try:
                            save_order_item(
                                upc,
                                product_number,
                                name,
                                order_number_text,
                                price,
                                store="Cub",
                            )
                        except Exception as e:
                            self.logger.error(f"Error saving order item: {e}")
                    else:
                        self.logger.warning(
                            f"Unexpected product text format: {product_text}"
                        )
                except Exception as e:
                    self.logger.error(f"Error parsing product: {e}")
        except TimeoutException:
            self.logger.error(
                "Failed to locate the order number element using all strategies."
            )
        except Exception as e:
            self.logger.error(f"Error in order parsing: {e}")

    def navigate_to_my_orders(self):
        """Navigates to the My Orders page and processes the first three orders."""
        try:
            self.log_info("Navigating to My Orders page...")
            # Locate and click the Account Button
            account_button = self.driver.find_element(
                By.XPATH, "//button[@id='AccountHeaderButton']"
            )
            self.driver.execute_script("arguments[0].click();", account_button)
            self.log_info("Clicked on Account Button.")
            time.sleep(2)

            # Locate and click the My Orders link
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

            order_details_summary = soup.find_all(
                "li", {"data-testid": lambda x: x and "order-details-summary" in x}
            )

            if not order_sections:
                self.logger.warning("No order sections found in the HTML.")
                return

            # Parse each order section
            for idx, section in enumerate(order_sections, start=1):
                self.logger.info(f"\n--- Order {idx} ---")
                order_details = self.parse_order_list(section)
                for key, value in order_details.items():
                    self.logger.info(f"{key}: {value}")

                # --- Extract the Order Details Summary ---
                order_details_summary = section.find(
                    "section", class_="OrderDetailsSummary--1qt8uu7 iDORIE"
                )
                if order_details_summary:
                    summary_details = self.parse_order_details_summary(
                        order_details_summary
                    )
                    self.logger.info("Order Details Summary:")
                    for key, value in summary_details.items():
                        self.logger.info(f"{key}: {value}")
                else:
                    self.logger.warning("Order Details Summary section not found.")
                    # Parse the full list of orders

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

                order = orders[orders_visited]  # Select different orders in each loop
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
        """
        Navigates to the order details page for a specific order.

        Args:
            order_element (WebElement): The WebElement representing the order in the list.
        """
        try:
            # Click on the order to navigate to its details
            order_link = order_element.find_element(By.TAG_NAME, "a")
            order_link.click()
            self.log_info("Navigated to order details page.")
        except Exception as e:
            self.logger.error(f"Error navigating to order details: {e}")
            raise

    def shutdown(self):
        """Closes the WebDriver instance and pops the application context."""
        self.driver.quit()
        self.logger.info("Browser closed.")

        # Pop the application context
        self.app_context.pop()
        self.logger.info("Application context popped.")

    def execute(self):
        """Runs the complete headless extraction process."""
        if self.login():
            self.navigate_to_my_orders()
            # self.print_visible_css_selectors()
        else:
            self.logger.error("Login failed. Extraction aborted.")
        self.shutdown()


if __name__ == "__main__":
    extractor = ExtractThinker()
    extractor.execute()
