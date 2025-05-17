
import os
import sys
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Add the backend directory to the Python path so that "app" is resolved correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Import your Flask application factory or app instance
from dotenv import load_dotenv

from app import create_app
# from app.services import save_product
from app.utils import setup_logger

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
        options.add_argument("--headless")              # Run Chrome in headless mode
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
            button_locate_strategies = [
                (By.CSS_SELECTOR, "button#AccountHeaderButton>span>div"),
                (By.XPATH, "//button[contains(text(), 'Sign In')")
            ]
            #Use the helper method to locate the element
            sign_in_button = self.locate_element_with_fallback(button_locate_strategies)
            # sign_in_button = self.driver.find_element(
            #     By.XPATH, "//button[contains(text(), 'Sign In')]"
            # )
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
                self.log_info(f"Trying to locate element using {by} with selector '{selector}'")
                element = self.wait.until(
                    EC.presence_of_element_located((by, selector))
                )
                self.log_info(f"Element found using {by}.")
                return element
            except TimeoutException:
                self.logger.warning(f"Element not found using {by} with selector '{selector}'.")
        self.logger.error("Element not found using all provided strategies.")
        raise TimeoutException("Element not found using all provided strategies.")

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
                  # Select different orders in each loop
                self.log_info(f"Processing order {orders_visited + 1} of {len(orders)}.")
                self.navigate_to_order_details(order)
                time.sleep(3)

                self.parse_my_orders()
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

    def get_order_details(self, order_number: str):
        """
        Finds an order detail element using its data-testid which includes the order_number_text,
        then parses its text to extract order number, order date, and total price.
        """
        # Build the XPath string using an f-string
        xpath = f"//section[@data-testid='order-card-info-testId-{order_number}']"

        # Find the element and get its text
        try:
            details_text = self.driver.find_element(by=By.XPATH, value=xpath).text
        except NoSuchElementException:
            self.logger.error(f"Element not found for order number: {order_number}")
            return None, None, None

        # Use BeautifulSoup to parse the details text
        soup = BeautifulSoup(details_text, 'html.parser')

        # Extract the order details
        order_number = soup.find('div', class_='order-number').get_text()
        order_date = soup.find('div', class_='order-date').get_text()
        total_price = soup.find('div', class_='total-price').get_text()

        return order_number, order_date, total_price


if __name__ == "__main__":
    extractor = ExtractThinker()
    extractor.execute()
