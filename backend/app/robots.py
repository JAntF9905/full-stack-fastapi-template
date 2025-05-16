import requests
from urllib.parse import urlparse


def get_robots_txt(url):
    """
    Fetches and parses the robots.txt file for a given URL.

    Args:
        url: The URL of the website.

    Returns:
        The content of the robots.txt file as a string, or None if not found or an error occurs.
    """
    try:
        parsed_url = urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        print(robots_url)
        response = requests.get(robots_url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching robots.txt: {e}")
        return None


if __name__ == "__main__":
    # List of websites to check
    websites = [
        "https://www.cub.com",
        "https://www.coborns.com",
        "https://www.walmart.com",
    ]
    # walmart_url = "https://www.walmart.com"  # Or any other URL

    for website in websites:
        print(f"\nChecking robots.txt for {website}")
        robots_content = get_robots_txt(website)
        if robots_content:
            print(website + ":\n" + robots_content)
