import json
import requests
from urllib.parse import urlparse
import time

def check_url_exists(url):
    """Check if a URL returns a valid response."""
    try:
        # Add headers to avoid being blocked by some servers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        # Consider 2xx and 3xx status codes as valid
        return response.status_code < 400
    except requests.exceptions.RequestException:
        return False

def main():
    # Load the JSON file
    with open('metadata.json', 'r') as f:
        data = json.load(f)
    
    # Track if we made any changes
    changes_made = False
    invalid_urls = []
    
    for idx, item in enumerate(data):
        # Task 1: Check and update sourceUrl
        key = item.get('key', '')
        source_url = item.get('sourceUrl', '')
        
        if key and source_url and key not in source_url:
            # Update the sourceUrl
            new_source_url = f"https://raw.githubusercontent.com/MicrosoftDocs/executable-docs/main/scenarios/{key}"
            print(f"Updating sourceUrl for '{key}':")
            print(f"  Old: {source_url}")
            print(f"  New: {new_source_url}")
            item['sourceUrl'] = new_source_url
            changes_made = True
        
        # Task 2: Check nextSteps URLs
        next_steps = item.get('nextSteps', [])
        for step_idx, step in enumerate(next_steps):
            url = step.get('url', '')
            if url:
                # Only check absolute URLs
                parsed = urlparse(url)
                if parsed.scheme in ['http', 'https']:
                    print(f"Checking URL: {url}")
                    if not check_url_exists(url):
                        invalid_urls.append({
                            'key': key,
                            'step_title': step.get('title', 'No title'),
                            'url': url,
                            'location': f"Item {idx}, nextStep {step_idx}"
                        })
                    # Add a small delay to be respectful to servers
                    time.sleep(0.5)
    
    # Save the updated JSON if changes were made
    if changes_made:
        with open('metadata.json', 'w') as f:
            json.dump(data, f, indent=4)
        print("\nUpdated metadata saved to 'metadata_updated.json'")
    
    # Print invalid URLs
    if invalid_urls:
        print("\n" + "="*80)
        print("INVALID URLs FOUND:")
        print("="*80)
        for invalid in invalid_urls:
            print(f"\nKey: {invalid['key']}")
            print(f"Step Title: {invalid['step_title']}")
            print(f"URL: {invalid['url']}")
            print(f"Location: {invalid['location']}")
    else:
        print("\nAll URLs are valid!")

if __name__ == "__main__":
    main()