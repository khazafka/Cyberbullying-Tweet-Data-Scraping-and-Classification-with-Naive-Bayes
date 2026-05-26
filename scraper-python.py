import os
import time
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from classifier import classify_tweet, sara_identity_keywords, sara_attack_keywords, flatten_keyword_dict

# Load environment variables from .env file
load_dotenv()

USERNAME = os.getenv("TWITTER_USERNAME")
PASSWORD = os.getenv("TWITTER_PASSWORD")
EMAIL = os.getenv("TWITTER_EMAIL")
AUTH_TOKEN = os.getenv("TWITTER_AUTH_TOKEN")
TARGET_TWEET_COUNT = 3000

def setup_browser():
    print("Booting up Edge browser...")
    edge_options = EdgeOptions()
    # Comment out the line below if you want to watch the browser work
    # edge_options.add_argument("--headless=new") # Disabled so you can see why login fails
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    # Commented out fake user-agent to prevent fingerprint mismatch
    # edge_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    edge_options.add_argument("--mute-audio")
    
    # Anti-bot detection bypass
    edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    edge_options.add_experimental_option('useAutomationExtension', False)
    edge_options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Modern Selenium automatically manages the driver
    driver = webdriver.Edge(options=edge_options)
    
    # Execute CDP command to hide webdriver flag from Javascript
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
        '''
    })
    
    return driver

def login_to_twitter(driver):
    if AUTH_TOKEN:
        print("Using Cookie Authentication...")
        # 1. Navigate to x.com first to set the cookie
        driver.get("https://x.com/404") 
        
        # 2. Add the auth_token cookie (domain omitted so Selenium infers it)
        driver.add_cookie({
            'name': 'auth_token',
            'value': AUTH_TOKEN,
            'path': '/',
            'secure': True
        })
        
        # 3. Refresh/navigate to home to apply the login
        print("Cookie injected. Navigating to home page...")
        driver.get("https://x.com/home")
        
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']")))
            print("\nLogin successful via cookies! Proceeding to scrape...")
            time.sleep(3)
            return
        except TimeoutException:
            print("[!] Cookie login failed. Your auth_token might be expired or invalid.")
            print("[!] Please get a fresh auth_token from your browser.")
            driver.save_screenshot("cookie_login_failed.png")
            raise Exception("Cookie login failed.")

    # Fallback to old manual/automated login if no token is provided
    print("No AUTH_TOKEN found. Navigating to Twitter login page...")
    driver.get("https://twitter.com/i/flow/login")
    wait = WebDriverWait(driver, 15)
    
    try:
        # 1. Enter Username
        print("Entering username...")
        username_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']")))
        username_field.send_keys(USERNAME)
        username_field.send_keys(Keys.RETURN)
        
        # 2. Handle unusual activity prompt if it appears
        time.sleep(2)
        try:
            password_field = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        except NoSuchElementException:
            print("Unusual activity detected. Attempting to enter email/phone verification...")
            # Twitter often uses data-testid="ocfEnterTextTextInput" for the verification box
            try:
                email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='ocfEnterTextTextInput']")))
            except TimeoutException:
                email_field = driver.find_element(By.CSS_SELECTOR, "input[name='text']")
            email_field.send_keys(EMAIL)
            email_field.send_keys(Keys.RETURN)
            time.sleep(2)
            
        # 3. Enter Password
        print("Entering password...")
        password_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']")))
        password_field.send_keys(PASSWORD)
        password_field.send_keys(Keys.RETURN)
        
    except Exception as e:
        print("\n[!] Automated login encountered an obstacle (e.g., Phone verification required, CAPTCHA, or changed UI).")
        print("[!] Please complete the login MANUALLY in the opened browser window.")
        print("[!] The script will wait up to 3 minutes for you to reach the home page...")
        pass # Fall through to the manual wait block
        
    try:
        # Wait for home page to load (long timeout to allow manual intervention)
        long_wait = WebDriverWait(driver, 180)
        long_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='primaryColumn']")))
        print("\nLogin successful! Proceeding to scrape...")
        time.sleep(3) 
    except TimeoutException:
        print("Timed out waiting for login to complete.")
        driver.save_screenshot("login_timeout.png")
        raise Exception("Login failed or timed out.")

def scrape_tweets():
    if not AUTH_TOKEN and (not USERNAME or not PASSWORD):
        print("Error: TWITTER_AUTH_TOKEN (or username/password) must be set in your .env file.")
        print("Please set TWITTER_AUTH_TOKEN for cookie authentication.")
        return

    scraped_data = []
    driver = setup_browser()
    
    try:
        login_to_twitter(driver)
        
        # Generate identity + attack combinations for searching
        identity_words = [item[0] for item in flatten_keyword_dict(sara_identity_keywords)]
        attack_words = [item[0] for item in flatten_keyword_dict(sara_attack_keywords)]
        
        search_queries = []
        
        # Batch attack words into chunks of 15 to stay within Twitter's search query limits
        chunk_size = 15
        attack_chunks = [attack_words[i:i + chunk_size] for i in range(0, len(attack_words), chunk_size)]
        
        for identity in identity_words:
            for chunk in attack_chunks:
                # Wrap multi-word attacks in quotes for Twitter search
                formatted_chunk = [f'"{w}"' if ' ' in w else w for w in chunk]
                attacks_str = " OR ".join(formatted_chunk)
                # Query matches the identity AND any of the attacks in the chunk, filtered to Indonesian
                query = f'"{identity}" ({attacks_str}) lang:id'
                search_queries.append(query)
                
        seen_tweet_ids = set()
        print(f"Generated {len(search_queries)} search queries combining identities and attacks. Target: {TARGET_TWEET_COUNT} tweets...")
        
        for keyword in search_queries:
            if len(scraped_data) >= TARGET_TWEET_COUNT:
                break
                
            print(f"\n--- Searching for query: {keyword} ---")
            # Navigate to search page (f=live gets the latest tweets)
            search_url = f"https://x.com/search?q={keyword}&src=typed_query&f=live"
            driver.get(search_url)
            
            try:
                wait = WebDriverWait(driver, 10)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']")))
            except TimeoutException:
                print(f"No tweets found or search failed for '{keyword}'. Skipping...")
                continue
            
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            tweets_for_keyword = 0
            
            while len(scraped_data) < TARGET_TWEET_COUNT and tweets_for_keyword < 50:
                # Find all visible tweets on the screen
                tweets = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
                
                for tweet in tweets:
                    try:
                        # Extract URL to get a unique identifier
                        time_elem = tweet.find_element(By.CSS_SELECTOR, "time")
                        link_elem = time_elem.find_element(By.XPATH, "..")
                        tweet_url = link_elem.get_attribute("href")
                        
                        if tweet_url in seen_tweet_ids:
                            continue
                            
                        seen_tweet_ids.add(tweet_url)
                        
                        # Extract text
                        try:
                            text_elem = tweet.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']")
                            tweet_text = text_elem.text
                        except NoSuchElementException:
                            tweet_text = "" 
                            
                        if not tweet_text.strip():
                            continue 
                            
                        # Extract username
                        user_elem = tweet.find_element(By.CSS_SELECTOR, "[data-testid='User-Name']")
                        user_text = user_elem.text.split('\n')
                        author_name = user_text[0] if len(user_text) > 0 else "Unknown"
                        username = user_text[1] if len(user_text) > 1 else "Unknown"
                        
                        if username.startswith('@'):
                            username = username[1:]
                            
                        is_bullying = classify_tweet(tweet_text)
                        
                        scraped_data.append({
                            'Username': username,
                            'Author Name': author_name,
                            'Tweet URL': tweet_url,
                            'Tweet Text': tweet_text,
                            'Is Cyberbullying (1/0)': is_bullying 
                        })
                        
                        tweets_for_keyword += 1
                        print(f"[{len(scraped_data)}/{TARGET_TWEET_COUNT}] Scraped tweet from @{username} (Keyword: {keyword})")
                        
                        if len(scraped_data) >= TARGET_TWEET_COUNT or tweets_for_keyword >= 50:
                            break
                            
                    except StaleElementReferenceException:
                        continue 
                    except Exception as e:
                        continue
                        
                if len(scraped_data) >= TARGET_TWEET_COUNT or tweets_for_keyword >= 50:
                    break

                # Scroll down to load more tweets
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3) 
                
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                    if scroll_attempts > 2:
                        print(f"Reached end of search results for '{keyword}'. Moving to next keyword.")
                        break
                else:
                    scroll_attempts = 0
                    last_height = new_height
                
    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        driver.save_screenshot("scraping_error.png")
        print("Saved screenshot of the error to 'scraping_error.png'")
    
    finally:
        print(f"\nFinished scraping. Saving {len(scraped_data)} rows to Excel...")
        driver.quit()
        
        if scraped_data:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            excel_path = os.path.join(script_dir, 'scraped_sara_data.xlsx')
            df = pd.DataFrame(scraped_data)
            df.to_excel(excel_path, index=False)
            print(f"Data successfully saved to {excel_path}")
        else:
            print("No data was scraped.")

if __name__ == '__main__':
    scrape_tweets()