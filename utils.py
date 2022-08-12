from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.core.utils import ChromeType
from selenium.webdriver.common.by import By

from dotenv import load_dotenv

load_dotenv()


def start_driver():
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument('--mute-audio')
    chrome_options.add_argument("--disable-infobars")
    # chrome_options.add_argument("--start-maximized")
    service = Service(ChromeDriverManager(
        # "2.26",
        # log_level=0,
        # print_first_line=False,
        chrome_type=ChromeType.GOOGLE).install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def get_tokens():
    driver = start_driver()
    driver.get('https://www.dice.com/dashboard/')
    driver.find_element(By.ID, 'email').send_keys('hamidnahlirss@gmail.com')
    driver.find_element(By.CSS_SELECTOR, '#loginDataSubmit > div:nth-child(3) > div > button').click()


submit_endpoint = 'https://api.prod.jobapplication-prod.dhiaws.com/graphql'
submit_body = {
    "operationName": "createApplication",
    "variables": {
        "input": {
            "candidate_id": "",
            "job_id": "a480bc60-9335-4eb6-b77f-e1b72f63aff2",
            "resume": None,
            "cover_letter": None,
            "screener": None,
            "ip_address": "",
            "correlation_id": "",
            "captchaToken": None
        }
    },
    "query": "mutation createApplication($input: ApplicationInput!) {   createApplication(input: $input) {     application_id     __typename   } } "
}
