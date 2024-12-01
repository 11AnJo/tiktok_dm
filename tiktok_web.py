import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from time import sleep
import logging
import sys
import os
import requests
import re
import time
from selenium.webdriver.common.keys import Keys
import random
from logging.handlers import RotatingFileHandler
import pyotp
from datetime import datetime, timedelta


class WaitAndClickException(Exception):
    pass


class WaitException(Exception):
    pass


def convert_to_int(value):
    value = value.strip()
    multiplier = 1
    if value.endswith('K'):
        multiplier = 1000
        value = value[:-1]
    elif value.endswith('M'):
        multiplier = 1000000
        value = value[:-1]
    elif value.endswith('B'):
        multiplier = 1000000000
        value = value[:-1]
    # try:
    return int(float(value) * multiplier)
    # except ValueError:
    #    return None


def ensure_logged(func):
    def wrapper(self, *args, **kwargs):
        if self.driver is None:
            self.logger.info("driver not active")
            self.driver = self._init_driver()

        if not self.is_logged:
            self.logger.info("login not active")
            self.login()

        return func(self, *args, **kwargs)
    return wrapper


LOCATORS = {
    "PROFILE_user-more_3_dots": '//div[@role="button" and @aria-label="Actions" and @data-e2e="user-more"]',
    "PROFILE_MORE_send_message": '//p[text()="Send message"]',
    "PROFILE_profile_not_found": '//p[text()="Couldn\'t find this account"]',
    "DM_input_box": '//div[@aria-label="Send a message..." and @role="textbox"]',
    "DM_send_button": '//div//*[@role="button" and @data-e2e="message-send"]',
    "DM_previous_msg": '//div[@data-e2e="chat-item"]',
    "DM_WARN": "//div[@data-e2e='dm-warning']//*[@xmlns='http://www.w3.org/2000/svg']",
    "DM_WARN_too_fast": "//div[text()='You are sending messages too fast. Take a rest.']",
    "DM_WARN_only_friends": "//div[text()='Only friends can send messages to each other']",
    "DM_WARN_privacy_settings": '//div[text()="Cannot send messages due to this user\'s privacy settings"]',
    "DM_WARN_privacy_settings_new": '//div[text()="This user is unable to receive your message due to this user\'s privacy settings"]',
    "DM_WARN_account_suspended": '//div[text()="The account you are trying to contact has been suspended and may not be able to receive your message."]',
    "DM_WARN_account_violated": '//div[text()="This account can\'t send or receive messages due to multiple Community Guidelines violations."]',
    "DM_WARN_privacy_settings_new_new": '//div[text()="The message couldn’t be sent due to receiver’s settings. We will resend the message once they update their permission."]',
    "DM_WARN_draft_violated_new": '//*[text()="This message violated our Community Guidelines. We restrict certain content and actions to protect our community. If you believe this was a mistake, tap "]',
    "DM_WARN_temporary_ban": '//*[text()="Due to multiple Community Guideline violations, you’re temporarily prevented from sending and receiving messages. View details in your app notifications."]',
    "DM_WARN_draft_violated": '//*[text()="This message violated our Community Guidelines. We restrict certain content and actions to protect our community. If you believe this was a mistake, tap"]',
    "DM_WARN_account_ban": '//*[text()="This account can’t send or receive messages due to multiple Community Guidelines violations."]',
    "DM_WARN_limit_reached": '//*[text()="Chat messages limit reached. You will not be able to send messages to this user."]',
    "SEARCH_no_more_results": '//div[text()="No more results"]',
    "SEARCH_user_container": '//div[@data-e2e="search-user-container"]',
    "SEARCH_user_container_href": './/a[@data-e2e="search-user-info-container"]',
    "SEARCH_user_followers": './/span[@data-e2e="search-follow-count"]',
    "INFO_followers": './/strong[@title="Followers" and @data-e2e="followers-count"]',
    "INFO_likes": './/strong[@title="Likes" and @data-e2e="likes-count"]',
    "CAPTCHA_exist": './/div[@role="dialog"]//div//div//a//span[text()="Report a problem"]',
    "LOGIN_email_or_username": './/input[@placeholder="Email or username"]',
    "LOGIN_password": './/input[@placeholder="Password"]',
    "LOGIN_2fa_otp":"//p[text()='Use the code from your authenticator app to verify your account.']",
    "LOGIN_2fa_mail":"//p[contains(text(),'Your code was emailed to ')]",
    "LOGIN_2fa_input": './/input[@placeholder="Enter 6-digit code"]',
    "LOGIN_2fa_submit": ".//button[@type='submit' and text()='Next']",
    "LOGIN__submit": ".//button[@type='submit' and text()='Log in']",
    "COOKIES_decline": ".//button[@text='Decline all']"
}


def initialize_log(name_of_log, debug=False):
    """
    Initialize a logger with two file handlers: one for normal logs and one for debug logs.
    The debug log file is limited to 1MB in size.
    """

    # Create the log directory if it doesn't exist
    log_dir = f'./log/{name_of_log}'
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)

    # Initialize the logger
    logger = logging.getLogger(name_of_log)
    logger.setLevel(logging.DEBUG)

    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create file handler for normal logging
    normal_log_file = os.path.join(log_dir, f"{name_of_log}.log")
    file_handler = logging.FileHandler(normal_log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Create file handler for debug logging with rotation
    debug_log_file = os.path.join(log_dir, f"{name_of_log}-debug.log")
    debug_file_handler = RotatingFileHandler(
        debug_log_file, maxBytes=1*1024*1024, backupCount=5, encoding='utf-8')
    debug_file_handler.setLevel(logging.DEBUG)
    debug_file_handler.setFormatter(formatter)
    logger.addHandler(debug_file_handler)

    # Stream handler to output to console
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


class Session:
    def __init__(self, profile_name=None, username=None, password=None, token=None, proxy=None, debug=False):
        self.profile_name = profile_name
        self.username = username
        self.password = password
        self.token = token
        self.is_logged = False
        self.proxy = proxy

        self.is_business = False
        self.logger = initialize_log(profile_name, debug)
        self.driver = None

    def _init_driver(self):
        options = uc.ChromeOptions()

        if not os.path.exists(f"{os.getcwd()}/profiles"):
            os.makedirs(f"{os.getcwd()}/profiles")

        if self.profile_name:
            data_dir = f"{os.getcwd()}/profiles/{self.profile_name}"
            options.add_argument(f"--user-data-dir={data_dir}")
        options.add_argument("--lang=en_US")
        options.add_argument("--mute-audio")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument('--disable-infobars')
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-site-isolation-trials")
        #options.add_argument("--headless=new")

        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")

        # options.add_argument('--headless=new')

        return uc.Chrome(options=options,
                         # driver_executable_path='chromedriver',
                         browser_executable_path=r"C:\\Users\\test\\Desktop\\chrome\\chrome.exe",
                         driver_executable_path="C:\\Users\\test\\Desktop\\chrome\\chromedriver.exe")
        # )

    def __wait_and_click(self, xpath, time=5, webelement=""):
        self.logger.debug(
            f'__wait_and_click() - called with xpath: {xpath}, time: {time}')
        try:
            button = WebDriverWait(self.driver if webelement == "" else webelement, time).until(
                EC.element_to_be_clickable((By.XPATH, xpath)))

            button.click()
            self.logger.debug(f"Clicked the element with xpath: {xpath}")
            return "clicked"
        except Exception as e:
            self.logger.debug(
                f"Could not click the element with xpath: {xpath}")
            if self.__is_element_present(LOCATORS["CAPTCHA_exist"], 0):
                # self.__wait_and_click('//*[@id="verify-bar-close"]')
                self.logger.warning(
                    "Found Captcha, please complete it and click enter to try again")
                input("Found Captcha")
                return self.__wait_and_click(xpath, time)

            raise WaitAndClickException(
                f"Stopping execution due to failure to click on element: {xpath}") from e

    def __wait(self, xpath, time=5, webelement=""):
        self.logger.debug(
            f'__wait() - called with xpath: {xpath}, time: {time}')
        try:
            return WebDriverWait(self.driver if webelement == "" else webelement, time).until(EC.presence_of_element_located((By.XPATH, xpath)))

        except Exception as e:
            self.logger.debug(
                f"Could not wait for the element with xpath: {xpath}")
            if self.__is_element_present(LOCATORS["CAPTCHA_exist"], 0):
                self.logger.warning(
                    "Found Captcha, please complete it and click enter to try again")
                input("Found Captcha,")
                return self.__wait_and_click(xpath, time)

            raise WaitException(
                f"Stopping execution due to failure in waiting for element: {xpath}") from e

    def __wait_for_all(self, xpath, time=5):
        self.logger.debug(
            f'__wait_for_all() - called with xpath: {xpath}, time: {time}')

        try:
            return WebDriverWait(self.driver, time).until(EC.presence_of_all_elements_located((By.XPATH, xpath)))
        except Exception as e:
            self.logger.debug(
                f"Could not wait for the element with xpath: {xpath}. Error: {str(e)}")
            raise WaitException(
                f"Stopping execution due to failure in waiting for element: {xpath}") from e

    def __paste_text(self, xpath, text, time_to_wait=0):
        self.logger.debug(
            f"__paste_text() called with xpath: {xpath}, text: {text}")

        action = ActionChains(self.driver)
        action.move_to_element(self.__wait(xpath, time_to_wait))
        action.click()
        action.send_keys(text)
        action.perform()

    def __is_element_present(self, xpath, time_to_wait=0):
        wait = WebDriverWait(self.driver, time_to_wait)
        self.logger.debug(
            f"__is_element_present() called with parameters: xpath: {xpath} time to wait: {time_to_wait}")

        try:
            wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            self.logger.debug("__is_element_present() returning True")
            return True
        except:
            self.logger.debug("__is_element_present() returning False")
            return False

    def __wait_for_first_element_or_url(self, elements, timeout=5):
        """
        Check the current URL or wait for the first element from the list of xpaths to be present.

        :param elements: List of URLs or XPath locators.
        :param timeout: Maximum time to wait for the elements or URLs.
        :return: Index of the first element or URL that appears, or -1 if none appear.
        """
        self.logger.debug(
            f'wait_for_first_element_or_url() - called with elements: {elements}, timeout: {timeout}')

        start_time = time.time()
        while time.time() - start_time < timeout:
            for index, element in enumerate(elements):
                try:
                    if element.startswith('http'):
                        if element in self.driver.current_url:
                            self.logger.debug(
                                f"current URL matches with index: {index}")
                            return index
                        time.sleep(0.05)
                    else:
                        WebDriverWait(self.driver, timeout=0.05).until(
                            EC.presence_of_element_located((By.XPATH, element)))
                        self.logger.debug(f"found element with index: {index}")
                        return index
                except TimeoutException:
                    pass  # Ignore timeout and check the next element or URL
                except Exception as e:
                    self.logger.debug(
                        f"Error while waiting for the element or URL: {element}. Error: {str(e)}")

        self.logger.debug(
            "No element or URL found/loaded within the timeout period.")
        return False

    def save_screenshot(self):
        name = time.asctime()
        self.logger.debug(f"saving screenshot with name: {name}.png")
        self.driver.save_screenshot(f"errors/{name}.png")

    def __put_cookie(self):
        # Create a date a few years in the future
        future_date = datetime.now() + timedelta(days=365*3)

        # Define the cookie
        cookie = {
            "name": "cookie-consent",
            "value": '{"ga":false,"af":false,"fbp":false,"lip":false,"bing":false,"ttads":false,"reddit":false,"hubspot":false,"version":"v10"}',
            "domain": ".tiktok.com",
            # Selenium expects expiry in seconds since epoch
            "expiry": int(future_date.timestamp()),
            "httponly": False,
            "secure": True,
            "samesite": "None"
        }

        # Add the cookie
        self.driver.add_cookie(cookie)

    def __send_in_chat(self,msg):      
        while True:
            if self.__wait(LOCATORS['DM_input_box']).text not in ['Send a message...','',None]:
                self.logger.info(self.__wait(LOCATORS['DM_input_box']).text)
                self.__wait(LOCATORS['DM_input_box']).send_keys(Keys.CONTROL + "a")
                self.__wait(LOCATORS['DM_input_box']).send_keys(Keys.DELETE)

            #self.__wait(LOCATORS['DM_input_box'])
            self.__paste_text(LOCATORS['DM_input_box'], msg)

            if self.__wait(LOCATORS['DM_input_box']).text == msg:
                try:
                    self.__wait_and_click(LOCATORS['DM_send_button'], 1)
                    self.__wait(LOCATORS['DM_previous_msg'], 5)

                    break
                except WaitException:
                    return 'try again'
            else: 
                continue

    @ensure_logged
    def send_msg(self, username, msg, send_if_msg_before=True):
        try:
            self.logger.debug(
                f"send_msg() called with arguments: username: {username}, msg: {msg}, send_if_msg_before: {send_if_msg_before}")
            if not username in self.driver.current_url:
                self.logger.debug("driver on other website. Redirecting ...")
                self.driver.get(f"https://www.tiktok.com/@{username}")
                sleep(1.5)
                if self.__is_element_present(LOCATORS['PROFILE_profile_not_found'], 0):
                    self.logger.debug("Profile not found")
                    return "Profile not found"

            self.__wait(LOCATORS['PROFILE_user-more_3_dots'], 10)

            page_source = self.driver.page_source
            user_id_match = re.search(
                r'(?<="userInfo":\{"user":\{"id":")\d{1,30}', page_source)
            user_id = user_id_match.group(0) if user_id_match else None
            self.logger.debug(f"user id is: {user_id}")

            if user_id is None:
                self.logger.error(
                    'Cannot find user_id in page source, trying again...')
                return "try again"

            if self.is_business:
                url = f"https://www.tiktok.com/messages?allow_label=true&lang=en&scene=business&u={user_id}"
            else:
                url = f"https://www.tiktok.com/messages?lang=en&u={user_id}"
            self.driver.get(url)

            try:
                self.__wait('//p[@data-e2e="chat-uniqueid"]', 60)
                sleep(0.5)
            except WaitException:
                self.logger.error("Cannot find dm input box")
                try:
                    self.driver.save_screenshot(
                        f"errors/dm_input_{time.time}.png")
                except:
                    self.logger.error("Cannot save screenshot")
                return 'try again'

            if send_if_msg_before == False:
                if self.__is_element_present(LOCATORS["DM_previous_msg"], 5):
                    self.logger.debug("Message before")
                    return "Message before"

            r = self.__send_in_chat(msg)
            if r:
                return r

            if self.__is_element_present(LOCATORS["DM_WARN"], 0):
                if self.__is_element_present(LOCATORS["DM_WARN_only_friends"]):
                    self.logger.info(
                        f"message not sent to {username} - Only friends")
                    return "Only friends"
                elif self.__is_element_present(LOCATORS["DM_WARN_too_fast"]):
                    self.logger.info(
                        f"message not sent to {username} - too fast")
                    return "too fast"
                elif self.__is_element_present(LOCATORS['DM_WARN_privacy_settings_new']):
                    self.logger.info(
                        f"message not sent to {username} - privacy settings new")
                    return "privacy settings"
                elif self.__is_element_present(LOCATORS['DM_WARN_privacy_settings']):
                    self.logger.info(
                        f"message not sent to {username} - privacy settings")
                    return "privacy settings"
                elif self.__is_element_present(LOCATORS['DM_WARN_account_suspended']):
                    self.logger.info(
                        f"message not sent to {username} - target account suspended")
                    return "target account suspended"
                elif self.__is_element_present(LOCATORS['DM_WARN_account_violated']):
                    self.logger.info(
                        f"message not sent to {username} - target account violated")
                    return "target account violated"
                elif self.__is_element_present(LOCATORS["DM_WARN_draft_violated"]):
                    self.logger.info(
                        f"draft violated, adding to banned_drafts.txt")
                    return "draft banned"
                elif self.__is_element_present(LOCATORS["DM_WARN_draft_violated_new"]):
                    self.logger.info(
                        f"draft violated, adding to banned_drafts.txt")
                    return "draft banned"
                elif self.__is_element_present(LOCATORS["DM_WARN_account_ban"]):
                    self.logger.info(
                        f"Target account banned")
                    return "target acc banned"
                elif self.__is_element_present(LOCATORS['DM_WARN_temporary_ban']):
                    self.logger.warning("Account temporarily banned")
                    return "acc banned"
                elif self.__is_element_present(LOCATORS['DM_WARN_privacy_settings_new_new']):
                    self.logger.info(
                        f"message not sent to {username} - privacy settings")
                    return "privacy settings"
                elif self.__is_element_present(LOCATORS['DM_WARN_limit_reached']):
                    self.logger.info(
                        f"message not sent to {username} - chat limit reached")
                    return "chat limit reached"

                else:
                    self.logger.info(
                        f"message not sent - Unknown DM warn - {username} id: {user_id}")
                    with open("error.html", "w", encoding='utf-8') as f:
                        f.write(self.driver.page_source)

                    return "Unknown DM warn"

            self.logger.info(f"message sent to {username}")
            return 'sent'

        except:
            self.logger.exception("Couldn't send message")
            return False

    @ensure_logged
    def start_for_check(self):
        pass

    @ensure_logged
    def search_usernames(self, searched_phrase, min_follow_count=0, skip_verified=False):
        self.logger.debug(
            f"search_usernames called with searched phrase: {searched_phrase}")

        def collect():
            usernames = set()
            repeated_count = 0
            threshold = 2  # Adjust the threshold as needed

            while True:
                try:
                    self.__wait(LOCATORS['SEARCH_user_container'], 10)
                except:
                    self.driver.refresh()
                    try:
                        self.__wait(LOCATORS['SEARCH_user_container'], 10)
                    except:
                        return None

                try:
                    elements = WebDriverWait(self.driver, 0).until(
                        EC.presence_of_all_elements_located((By.XPATH, LOCATORS['SEARCH_user_container'])))
                except WaitException:
                    self.logger.info(
                        f"no usernames found with search phrase: {searched_phrase}, trying again")
                    try:
                        elements = WebDriverWait(self.driver, 0).until(
                            EC.presence_of_all_elements_located((By.XPATH, LOCATORS['SEARCH_user_container'])))
                    except WaitException:
                        self.logger.error(
                            f"no usernames found with search phrase: {searched_phrase}")
                        return usernames

                old_len = len(usernames)
                for el in elements:
                    username = el.find_element(by=By.XPATH, value=LOCATORS['SEARCH_user_container_href']).get_attribute(
                        "href").replace("https://www.tiktok.com/@", "").replace("?lang=en", "")

                    # -------skip if verified
                    if skip_verified:
                        a = 0
                        spans = el.find_elements(by=By.XPATH, value='.//span')
                        for span in spans:
                            if "SpanVerifyBadgeContainer" in span.get_attribute('class'):
                                a += 1
                        if a != 0:
                            self.logger.debug("Skip - Account verified")
                            continue
                    # -------

                    try:
                        followers_text = el.find_element(
                            by=By.XPATH, value=LOCATORS['SEARCH_user_followers']).text
                        followers = convert_to_int(followers_text)
                    except:
                        self.logger.debug(
                            f"username: {username} found but followers not")
                        continue

                    self.logger.debug(
                        f"followers: {followers}, min_follow_count: {min_follow_count}")
                    if followers < min_follow_count:
                        self.logger.debug(
                            "Skip - followers are less than specified minimum. ")
                        continue
                    # print(username,followers)
                    usernames.add(username)

                if old_len == len(usernames):
                    repeated_count += 1
                    if repeated_count >= threshold:
                        break
                else:
                    repeated_count = 0

                self.driver.execute_script(
                    "arguments[0].scrollIntoView();", elements[-1])
                sleep(1)
            return usernames

        self.driver.get(
            f"https://www.tiktok.com/search/user?lang=en&q={searched_phrase}")
        usernames = collect()
        return usernames

    @ensure_logged
    def get_user_info(self, username):
        self.logger.debug(f"get_user_info() called with: username: {username}")

        try:
            self.driver.get(f"https://www.tiktok.com/@{username}")
            if self.__is_element_present(LOCATORS['PROFILE_profile_not_found'], 0):
                self.logger.debug("Profile not found")
                return "Profile not found"

            followers_count = convert_to_int(self.__wait(
                LOCATORS['INFO_followers'], time=5).text)
            likes_count = convert_to_int(self.__wait(
                LOCATORS['INFO_likes'], time=5).text)
            return {"followers": followers_count, "likes": likes_count}
        except:
            self.logger.exception("could not scrape user data")
            return "could not scrape user data"

    @ensure_logged
    def dm_blocker_deleter(self):     

        self.driver.get('https://www.tiktok.com/messages?lang=en')

        try:
            self.__wait('//div[@data-e2e="chat-list-item"]',10)
        except WaitException:
            return 'chats not loading or all messages done'

        while True:
            #self.driver.get('https://www.tiktok.com/messages?lang=en')

            if self.__is_element_present('//p[contains(@class, "InfoNickname") and string-length(text()) > 0]',10):
                chat_item = self.__wait_for_all('//p[contains(@class, "InfoNickname") and string-length(text()) > 0]')[0]

                ActionChains(self.driver).scroll_to_element(chat_item).perform()
                ActionChains(self.driver).move_to_element(chat_item).perform()
                sleep(1)
                input('click more action')
                self.__wait_and_click('//*[@data-e2e="more-action-icon"]',5,chat_item)

                if self.__is_element_present('//p[text()="Block"]') :
                    input('block?')
                    self.__wait_and_click('//p[text()="Block"]')
                    ActionChains(self.driver).scroll_to_element(chat_item).perform()
                    ActionChains(self.driver).move_to_element(chat_item).perform()
                    

                    input('click more actions')
                    self.__wait_and_click('//*[@data-e2e="more-action-icon"]',5,chat_item)
                    
                    input('delete')
                    self.__wait_and_click('//p[text()="Delete"]/..//*[@fill="currentColor"]')

                else:
                    print('blocked')
                    input('delete')

                    self.__wait_and_click('//p[text()="Delete"]/..//*[@fill="currentColor"]')

                #input('next?')
            elif self.__is_element_present('//div[@data-e2e="chat-list-item"]'):
                self.driver.get('https://www.tiktok.com/messages?lang=en')
                try:
                    self.__wait('//div[@data-e2e="chat-list-item"]',10)
                except WaitException:
                    self.logger.info('All finished!')
                    return 'all messages done'




    @ensure_logged 
    def dm_deleter(self):
        self.driver.get('https://www.tiktok.com/messages?lang=en')
        sleep(10)

        while self.__is_element_present('//*[@data-e2e="chat-list-item"]', 200):
            chat_item = self.__wait('//*[@data-e2e="chat-list-item"]', 200)

            actions = ActionChains(self.driver)
            actions.move_to_element(chat_item).perform()
            print("waiting...")

            self.__wait_and_click('//*[@data-e2e="more-action-icon"]')

            self.__wait('//p[text()="Delete"]', 2)
            self.__wait_and_click(
                '//p[text()="Delete"]/..//*[@fill="currentColor"]')
            sleep(0.2)

        self.logger.info('All finished!')

    @ensure_logged
    def video_deleter(self):
        self.driver.get(f'https://www.tiktok.com/@{self.profile_name}')
        sleep(5)

        self.__wait_and_click(
            '//div[@role="button" and @data-e2e="user-post-item"]')

        while self.__is_element_present('//div[@data-e2e="video-setting"]'):
            self.__wait_and_click('//div[@data-e2e="video-setting"]')
            self.__wait_and_click('//*[text()="Delete"]')
            self.__wait_and_click('//button[@data-e2e="video-modal-delete"]')
            sleep(0.5)

            if not self.__is_element_present('//div[@data-e2e="video-setting"]', 5):
                self.video_delete()
            # if not self.__is_element_present('//*[text()="Delete"]', 5):
            #    self.video_delete()
            # if not self.__is_element_present('//button[@data-e2e="video-modal-delete"]', 5):
            #    self.video_delete()

        self.logger.info('All finished!')

    @ensure_logged
    def favorite_delete(self):
        self.driver.get(f'https://www.tiktok.com/@{self.profile_name}')
        sleep(5)

        self.__wait_and_click('//span[text()="Favorites"]')
        self.__wait_and_click('//div[@data-e2e="favorites-item"]')

        try:
            while self.__is_element_present('//span[@data-e2e="undefined-icon"]'):
                self.__wait_and_click('//span[@data-e2e="undefined-icon"]')
                self.__wait_and_click('//button[@data-e2e="arrow-right"]')
                sleep(0.5)
        except:
            if not self.__is_element_present('//button[@data-e2e="arrow-right"]'):
                self.logger.info('All finished!')

    @ensure_logged
    def liked_delete(self):
        self.driver.get(f'https://www.tiktok.com/@{self.profile_name}')
        sleep(5)

        self.__wait_and_click('//p[@data-e2e="liked-tab"]')
        self.__wait_and_click('//div[@data-e2e="user-liked-item"]')

        try:
            while self.__is_element_present('//span[@data-e2e="browse-like-icon"]'):
                self.__wait_and_click('//span[@data-e2e="browse-like-icon"]')
                self.__wait_and_click('//button[@data-e2e="arrow-right"]')
                sleep(0.2)
        except:
            if not self.__is_element_present('//button[@data-e2e="arrow-right"]'):
                self.logger.info('All finished!')

    @ensure_logged
    def unfollower(self):
        self.driver.get(f'https://www.tiktok.com/@{self.profile_name}')
        sleep(5)

        # Click on the 'following' span if present
        if self.__is_element_present('//div//span[@data-e2e="following"]'):
            self.__wait_and_click('//div//span[@data-e2e="following"]')

        sleep(1)
        
        while True:
            try:
                following_clicked = False
                friends_clicked = False

                # Check and click 'Following' button
                if self.__is_element_present('//div//button[text()="Following"]'):
                    self.__wait_and_click('//button[text()="Following"]')
                    following_clicked = True

                # Check and click 'Friends' button
                if self.__is_element_present('//button[text()="Friends"]'):
                    self.__wait_and_click('//button[text()="Friends"]')
                    friends_clicked = True

                # If neither button was clicked, exit the loop
                if not following_clicked and not friends_clicked:
                    self.logger.info('All finished!')
                    return 'All finished!'

            except Exception as e:
                self.logger.error(f'Error: {e}')
                if not (self.__is_element_present('//button[text()="Following"]') or self.__is_element_present('//button[text()="Friends"]')):
                    self.logger.info('All finished!')
                    return 'All finished!'

    @ensure_logged
    def unarchiver(self):
        self.driver.get(f'https://www.tiktok.com/@{self.profile_name}')
        sleep(5)

        self.__wait_and_click(
            '//div[@role="button" and @data-e2e="user-post-item"]')

        while True:

            # Check if the video is private
            if self.__is_element_present(".//span[text()='Private']"):
                # Click to open the video settings
                self.__wait_and_click('.//div[@data-e2e="video-setting"]')
                sleep(1)

                # Click to open privacy settings
                self.__wait_and_click('.//*[text()="Privacy settings"]')
                sleep(1)

                # Change privacy to public
                self.__wait_and_click('.//*[@data-e2e="video-setting-choose"]')
                sleep(1)  # Wait for the click to take effect
                self.__wait_and_click('.//p[text()="Everyone"]')
                sleep(1)  # Wait for the click to take effect

                # Click "Done" text
                self.__wait_and_click(
                    './/button[@data-e2e="video-setting-down"]')
            else:
                # If Private is not available, skip video.
                self.__wait_and_click(".//button[@data-e2e='arrow-right']")

    def __generate_2factor_code(self, token):
        totp = pyotp.TOTP(token)
        current_time = time.time()
        time_step = 30  # TOTP time step, usually 30 seconds
        remaining_time = time_step - (current_time % time_step)

        # If the code is valid for less than 5 seconds, wait for the next one
        if remaining_time < 4:
            time.sleep(remaining_time)

        new_code = totp.now()
        return new_code

    
    def login(self):
        if self.driver is None:
            self.driver = self._init_driver()

        def wait_for_possible_el():
            return self.__wait_for_first_element_or_url([
                LOCATORS['CAPTCHA_exist'],
                LOCATORS['LOGIN_2fa_otp'],
                LOCATORS['LOGIN_2fa_mail'],
                "https://www.tiktok.com/foryou",

            ], 20)

        self.logger.debug(f"login() called")

        self.driver.get('https://tiktok.com/messages?lang=en')
        time.sleep(2)
        if 'https://www.tiktok.com/login' not in self.driver.current_url:
            if '/business-suite/messages' in self.driver.current_url:
                self.logger.info('business account detected')
                self.is_business = True
            self.is_logged = True
            return True

        if self.username == None or self.password == None:
            self.logger.error(
                "Username or password not provided login by yourself and click 'Y'")
            y = input('continue? [y/n]: ')
            if y.lower() == 'y':
                return True
            return False
        self.__put_cookie()
        time.sleep(1)
        self.driver.get('https://www.tiktok.com/login/phone-or-email/email')

        if not self.__is_element_present(LOCATORS['LOGIN_email_or_username'], 10):
            self.logger.error("Could not find the login page")
            return False

        time.sleep(1)
        self.__paste_text(
            LOCATORS['LOGIN_email_or_username'], self.username, 0)
        time.sleep(1)
        self.__paste_text(LOCATORS['LOGIN_password'], self.password, 0)
        time.sleep(1)
        self.__wait_and_click(LOCATORS['LOGIN__submit'], 2)

        resp = wait_for_possible_el()

        def when_captcha():
            self.logger.warning(
                "Found Captcha, please complete it manually")

            while True:
                if self.__is_element_present(LOCATORS['CAPTCHA_exist'], 0):
                    time.sleep(1)
                    continue
                time.sleep(1)
                break
        if resp == 0:
            when_captcha()
            resp = wait_for_possible_el()


        if resp == 1:
            self.logger.debug("2fa input found")
            code = self.__generate_2factor_code(self.token)
            self.__paste_text(LOCATORS['LOGIN_2fa_input'], code, 0)
            time.sleep(1)
            self.__wait_and_click(LOCATORS['LOGIN_2fa_submit'], 0)
            resp = wait_for_possible_el()
            if resp == 0:
                when_captcha()
                resp = wait_for_possible_el()

        if resp == 2:
            self.logger.debug("2fa mail input found")
            self.logger.warning('mail 2fa found.')
            input('paste the code and click enter')
            self.__wait_and_click(LOCATORS['LOGIN_2fa_submit'], 0)

            resp = wait_for_possible_el()
            if resp == 0:
                when_captcha()
                resp = wait_for_possible_el()


        if resp == 3:
            self.is_logged = True
            # self.__wait_and_click(LOCATORS['COOKIES_decline'],1)
            # time.sleep(2)\
            self.driver.get('https://tiktok.com/messages?lang=en')
            return True

        if resp == False:
            self.logger.error("Could not login")
            self.__save_error_screenshot()
            return False
