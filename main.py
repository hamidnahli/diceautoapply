import requests
import os
from typing import List
import logging
from multiprocessing import get_logger
from urllib.parse import urlencode
import time
from random import randint

from colorama import Fore
from colorama import Style

from bs4 import BeautifulSoup

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.core.utils import ChromeType
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from dotenv import load_dotenv

load_dotenv()


def delay():
    # log.info('sleeping for sometime to before applying to the next job')
    time.sleep(randint(15, 45))


def logger(level=logging.INFO) -> logging.getLogger:
    log = get_logger()
    log.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(asctime)s - %(process)s - %(message)s'
    ))
    log.addHandler(handler)
    return log


def start_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
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
    driver.find_element(By.ID, 'email').send_keys(os.getenv('EMAIL'))
    driver.find_element(By.ID, 'password').send_keys(os.getenv('PASSWORD'))
    driver.find_element(By.CSS_SELECTOR, '#loginDataSubmit > div:nth-child(3) > div > button').click()
    cookies_ = driver.get_cookies()
    authorization_ = [ele['value'] for ele in cookies_ if ele['name'] == 'access'][0]
    candidate_id_ = [ele['value'] for ele in cookies_ if ele['name'] == 'candidate_id'][0]
    # scrap authToken
    driver.get(
        'https://www.dice.com/jobs?q=python%20developer&location=New%20York,%20NY,%20USA&latitude=40.7127753&longitude=-74.0059728&countryCode=US&locationPrecision=City&radius=30&radiusUnit=mi&page=1&pageSize=100&filters.employmentType=FULLTIME%7CCONTRACTS&filters.easyApply=true&language=en&eid=S2Q_,gKQ_')
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    auth_token_ = soup.find('dhi-js-dice-client')['auth-token']
    driver.quit()
    return authorization_, candidate_id_, auth_token_, cookies_


def get_job_id(legacy_id):
    host = 'https://jobs-graphql.prod.jobs-prod.dhiaws.com/graphql'
    headers = {
        'Host': 'jobs-graphql.prod.jobs-prod.dhiaws.com',
        'Sec-Ch-Ua': '" Not A;Brand";v="99", "Chromium";v="104"',
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'Sec-Ch-Ua-Mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.81 Safari/537.36',
        'Origin': 'https://www.dice.com',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://www.dice.com/',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    body = {
        "operationName": "getJobId",
        "variables": {"legacyJobId": legacy_id},
        "query": "query getJobId($legacyJobId: String) {\n  getJobId(legacyJobId: $legacyJobId) {\n    jobId\n    __typename\n  }\n}\n"
    }
    response = requests.post(host, headers=headers, json=body)
    data = response.json()
    job_id = data['data']['getJobId']['jobId']
    return job_id


def get_geo_data(city, stat):
    driver = start_driver()
    driver.get('https://www.google.com/maps/')
    driver.find_element(By.ID, 'searchboxinput').send_keys(f'{city} {stat}')
    driver.find_element(By.ID, 'searchboxinput').send_keys(Keys.ENTER)
    while '@' not in driver.current_url:
        time.sleep(1)
    url = driver.current_url.split('/')
    data = [ele for ele in url if '@' in ele][0][1:]
    latitude, longitude, _ = data.split(',')
    driver.quit()
    return latitude, longitude


def search_jobs(query: dict) -> List:
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://www.dice.com',
        'referer': 'https://www.dice.com/',
        'sec-ch-ua': '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
        'sec-ch-ua-mobile': '?0',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
        'x-api-key': '1YAt0R9wBg4WfsF9VB2778F5CHLAPMVW3WAZcKd8',
    }
    url_query = urlencode(query)
    url = f'https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search?{url_query}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()['data']
        if len(data) != 0:
            query['page'] = str(int(query['page']) + 1)
            data = data + search_jobs(query)
        return data


def get_applied_jobs(cookies, page):
    data = []
    s = requests.Session()
    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'])
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Host': 'www.dice.com',
        'If-Modified-Since': '0',
        'Referer': 'https://www.dice.com/dashboard/jobs',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
        'sec-ch-ua': '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
        'sec-ch-ua-mobile': '?0',
    }
    url = f'https://www.dice.com/config/dice/api.json?path=%2Fpeople%2F15670183%2Fapplications%3FincludeExpired%3Dfalse%26page%3D{page}%26count%3D100'
    response = s.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()['documents']
        data = data + get_applied_jobs(cookies, page + 1)
    return data


def apply(legacy_id, authorization_, auth_token_, candidate_id_, jobs_):
    if jobs_:
        jobs_ = [ele['jobId'] for ele in jobs_]
        if legacy_id in jobs_:
            return log.info(f'already applied for {legacy_id}')
    job_id = get_job_id(legacy_id)
    headers = {
        'Sec-Ch-Ua': '" Not A;Brand";v="99", "Chromium";v="104"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Authorization': authorization_,
        'Content-Type': 'application/json',
        'Accept': '*/*',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
        'X-Legacy-Auth': auth_token_,
        'Origin': 'https://www.dice.com',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        'Referer': 'https://www.dice.com/',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    host = 'https://api.prod.jobapplication-prod.dhiaws.com/graphql'
    body = {
        "operationName": "createApplication",
        "variables": {
            "input": {
                "candidate_id": candidate_id_,
                "job_id": job_id,
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
    response = requests.post(host, headers=headers, json=body)
    data = response.json()['data']
    if data.get('createApplication')['__typename'] == 'CreateApplicationOutput':
        delay()
        return log.info(f'{Fore.GREEN}successfully applied to {legacy_id}!{Style.RESET_ALL}')
    return log.error(f'{Fore.RED}failed to applied to {legacy_id}!{Style.RESET_ALL}')


search_query = {
    'q': 'python developer',
    'locationPrecision': 'City',
    'latitude': '29.7604267',
    'longitude': '-95.3698028',
    'countryCode2': 'US',
    'radius': '30',
    'radiusUnit': 'mi',
    'page': '1',
    'pageSize': '100',
    'facets': 'employmentType|postedDate|workFromHomeAvailability|employerType|easyApply|isRemote',
    'filters.employmentType': 'FULLTIME|CONTRACTS',
    'filters.easyApply': 'true',
    'fields': 'id|jobId|summary|title|postedDate|modifiedDate|jobLocation.displayName|detailsPageUrl|salary|clientBrandId|companyPageUrl|companyLogoUrl|positionId|companyName|employmentType|isHighlighted|score|easyApply|employerType|workFromHomeAvailability|isRemote',
    'culture': 'en',
    'recommendations': 'true',
    'interactionId': '0',
    'fj': 'true',
    'includeRemote': 'true',
    'eid': 'a6zd7NUgR0Wy8Tzf36TS2Q_|2_bFbpyKRTuIwPOz6UkgKQ_'
}
emp_types = {0: 'PARTTIME', 1: 'FULLTIME', 2: 'CONTRACTS', 3: 'FULLTIME|CONTRACTS'}
log = logger()

if __name__ == '__main__':
    # Getting user desired search criteria.
    search_keyword = input("Job title: ")
    city = input("City: ")
    state = input("State: ")
    input_type = int(input("Employment Type: 0 - PARTTIME, 1 - FULLTIME, 2 - CONTRACTS, 3 - Both "))
    employment_type = emp_types[input_type]
    # Updating the search query
    log.info(f'getting geodata for {city}, {state} from google maps')
    latitude, longitude = get_geo_data(city, state)
    search_query.update(
        {
            'q': search_keyword,
            'latitude': latitude,
            'longitude': longitude,
            'filters.employmentType': employment_type
        }
    )
    # Getting tokens:
    log.info(f'scraping tokens for authentication')
    authorization, candidate_id, auth_token, cookies = get_tokens()

    # Retrieve jobs already applied for
    log.info(f'retrieving jobs already applied for')
    applied_jobs = get_applied_jobs(cookies, 1)
    found_jobs = search_jobs(search_query)
    log.info(f'found {len(found_jobs)} jobs matching the search criteria')
    for job in found_jobs:
        apply(job['id'], authorization, auth_token, candidate_id, applied_jobs)

