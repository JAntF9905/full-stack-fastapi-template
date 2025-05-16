import os
import time

from playwright.sync_api import sync_playwright


def run():
    username = os.getenv("CUB_USERNAME")
    password = os.getenv("CUB_PASSWORD")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.cub.com")

        # Debug: Screenshot and HTML after initial load
        page.screenshot(path="debug_initial.png")
        print("[DEBUG] Initial page content:")
        print(page.content())

        # Check for modal presence
        modal_present = False
        try:
            modal = page.query_selector("#outside-modal")
            if modal:
                modal_present = True
                print("[DEBUG] Modal found before attempting to close.")
            else:
                print("[DEBUG] Modal NOT found before attempting to close.")
        except Exception as e:
            print(f"[DEBUG] Error checking for modal: {e}")

        # Try to close modal if present
        for _ in range(3):
            try:
                page.click("#outside-modal", timeout=2000)
                page.wait_for_selector("#outside-modal", state="detached", timeout=2000)
                print("[DEBUG] Modal clicked and waited for detachment.")
                break
            except Exception as e:
                print(f"[DEBUG] Exception while closing modal: {e}")
                break

        # Debug: Screenshot and HTML after modal handling
        page.screenshot(path="debug_after_modal.png")
        print("[DEBUG] Page content after modal handling:")
        print(page.content())

        # Check for Sign In button
        try:
            sign_in_btn = page.query_selector("button#AccountHeaderButton")
            if sign_in_btn:
                print("[DEBUG] 'AccountHeaderButton' found.")
            else:
                print("[DEBUG] 'AccountHeaderButton' NOT found.")
        except Exception as e:
            print(f"[DEBUG] Error checking for 'AccountHeaderButton': {e}")

        # Wait a bit for UI to settle
        time.sleep(2)

        # Now click "Sign In"
        try:
            page.click("button#AccountHeaderButton >> text=Sign In")
            print("[DEBUG] Clicked 'Sign In' button.")
        except Exception as e:
            print(f"[DEBUG] Exception clicking 'Sign In': {e}")
            page.screenshot(path="debug_signin_fail.png")
            print("[DEBUG] Page content at Sign In failure:")
            print(page.content())
            raise

        # Fill in login form
        page.fill("#signInName", username)
        page.fill("#password", password)
        page.click("button:has-text('Continue')")

        # Wait for login to complete
        page.wait_for_selector("button#AccountHeaderButton:has-text('My Account')", timeout=10000)

        # Navigate to My Orders
        page.click("button#AccountHeaderButton")
        page.click("text=My Orders")
        page.wait_for_selector("ul[data-testid='orders-list-testId']")

        # Example: Print order numbers
        orders = page.query_selector_all("span[data-testid^='order-number-testId']")
        for order in orders[:3]:
            print("Order:", order.inner_text())

        page.screenshot(path="debug.png")
        print(page.content())

        browser.close()

if __name__ == "__main__":
    run()
