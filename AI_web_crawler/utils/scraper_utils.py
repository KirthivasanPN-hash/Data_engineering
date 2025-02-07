import json
import os

from typing import List, Set, Tuple

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig, # Dictates how browser is launched and behaves (headless, or visible, proxy, user agent)
    CacheMode, # Dictates how caching is done (eg. no cache, cache on disk, cache in memory)
    CrawlerRunConfig, # Dictates how each crawler operates (eg caching, extraction, timeouts, JavaScript code to run)
    LLMExtractionStrategy, # Dictates how to extract data from the page (eg. CSS selector, XPath, regex)
)

from models.site import Site
from utils.data_utils import is_duplicate, is_complete_site


def get_browser_config() -> BrowserConfig:
    """
    Return the browser configuration.
    """
    
    return BrowserConfig(
        browser_type = "chromium",
        headless = True, # False for running in headless mode (no GUI)
        verbose = True, # logging
    )

def get_llm_strategy() -> LLMExtractionStrategy:
    """
    Return the LLM strategy. The settings for how to extract data using LLM.
    """
    return LLMExtractionStrategy(
        provider = "openai/gpt-4o",
        api_token = os.getenv("OPENAI_API_KEY"),
        schema = Site.model_json_schema(),
        extraction_type = "schema",
        instruction=(
                "Extract all venue objects with 'name', 'location', 'price', 'capacity', "
                "'rating', 'reviews', and a 1 sentence description of the venue from the "
                "following content."
            ),  # Instructions for the LLM
        input_from = "markdown",
        verbose = True,
)

async def check_no_results(
        crawler: AsyncWebCrawler,
        url: str,
        session_id: str,
        
) -> bool:
    """
    Check if the page has no results.

    Args:
        crawler: The crawler object
        url (str): The URL to check
        session_id(str): The session identifier

    """
    result = await crawler.arun(
        url = url,
        config = CrawlerRunConfig(
            cache_mode = CacheMode.BYPASS,
            session_id = session_id,

        ),

    )
    
    if result.success:
        if "No Results Found" in result.cleaned_html:
            return True
        
        else:
            print(f"Error fetching page for 'No Results Found' check: {result.error_message} ")
    return False


async def fetch_and_process_page(
    crawler: AsyncWebCrawler,
    page_number: int,
    base_url: str,
    css_selector: str,
    llm_strategy: LLMExtractionStrategy,
    session_id: str,
    required_keys: List[str],
    seen_names: Set[str],
) -> Tuple[List[dict], bool]:
    """
    Fetches and processes a single page of venue data.

    Args:
        crawler (AsyncWebCrawler): The web crawler instance.
        page_number (int): The page number to fetch.
        base_url (str): The base URL of the website.
        css_selector (str): The CSS selector to target the content.
        llm_strategy (LLMExtractionStrategy): The LLM extraction strategy.
        session_id (str): The session identifier.
        required_keys (List[str]): List of required keys in the venue data.
        seen_names (Set[str]): Set of venue names that have already been seen.

    Returns:
        Tuple[List[dict], bool]:
            - List[dict]: A list of processed venues from the page.
            - bool: A flag indicating if the "No Results Found" message was encountered.
    """
    url = f"{base_url}?page={page_number}"
    print(f"Loading page {page_number}...")

    # Check if "No Results Found" message is present
    no_results = await check_no_results(crawler, url, session_id)
    if no_results:
        return [], True  # No more results, signal to stop crawling

    # Fetch page content with the extraction strategy
    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,  # Do not use cached data
            extraction_strategy=llm_strategy,  # Strategy for data extraction
            css_selector=css_selector,  # Target specific content on the page
            session_id=session_id,  # Unique session ID for the crawl
        ),
    )

    if not (result.success and result.extracted_content):
        print(f"Error fetching page {page_number}: {result.error_message}")
        return [], False

    # Parse extracted content
    extracted_data = json.loads(result.extracted_content)
    if not extracted_data:
        print(f"No venues found on page {page_number}.")
        return [], False

    # After parsing extracted content
    print("Extracted data:", extracted_data)

    # Process data
    complete_info = []
    for info in extracted_data:
        # Debugging: Print each venue to understand its structure
        print("Processing data:", info)

        # Ignore the 'error' key if it's False
        if info.get("error") is False:
            info.pop("error", None)  # Remove the 'error' key if it's False

        if not is_complete_site(info, required_keys):
            continue  # Skip incomplete venues

        if is_duplicate(info["name"], seen_names):
            print(f"Duplicate venue '{info['name']}' found. Skipping.")
            continue  # Skip duplicate venues

        # Add venue to the list
        seen_names.add(info["name"])
        complete_info.append(info)

    if not complete_info:
        print(f"No complete venues found on page {page_number}.")
        return [], False

    print(f"Extracted {len(complete_info)} venues from page {page_number}.")
    return complete_info, False  # Continue crawling