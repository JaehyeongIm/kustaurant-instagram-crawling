from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

import time
import re

from dotenv import load_dotenv
import os

load_dotenv()

INSTAGRAM_ID = os.getenv("INSTAGRAM_ID")
INSTAGRAM_PW = os.getenv("INSTAGRAM_PW")

TARGET_PROFILE = 'https://www.instagram.com/alliance.student.konkuk/'
category = 7 # 7은 카페, 8은 음식점, 9는 호프집
result_lst=[]
def login_instagram(driver):
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(3)
    username_input = driver.find_element(By.NAME, "username")
    password_input = driver.find_element(By.NAME, "password")
    
    username_input.send_keys(INSTAGRAM_ID)
    password_input.send_keys(INSTAGRAM_PW)
    password_input.send_keys(Keys.RETURN)
    time.sleep(7)

def collect_links(driver, category):

    driver.get(TARGET_PROFILE)
    time.sleep(5)

    story_icon = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, f'//ul/li[{category}]/div/div/div'))
    )
    story_icon.click()
    time.sleep(3)

    collected_links = []

    story_slides = driver.find_elements(By.CSS_SELECTOR, "div.x1ned7t2.x78zum5 > div.x1lix1fw.xm3z3ea")
    print("가게 개수:",len(story_slides))
    for i in range(len(story_slides)):
        try:
            # 게시물 보기 유도용 클릭
            try:
                story_content = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[@role="button" and @style][contains(@style, "translate")]'))
                )
                ActionChains(driver).move_to_element(story_content).click().perform()
                time.sleep(2)
            except:
                pass  # 없으면 넘어감

            post_button = driver.find_elements(By.XPATH, '//div[@role="dialog"]//a[@role="link"]')
            if post_button:
                href = post_button[0].get_attribute("href")
                print(href, post_button)
                if href and href not in collected_links:
                    collected_links.append(href)
                    print(f"🔗 링크 수집됨: {href}")
            try:
                # 다음 스토리로 이동
                next_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div/div/div[3]/div/div/div[3]/div/section/div[1]/div/div[5]/div/div[2]/div[2]/div'))
                )
                time.sleep(1)
                next_btn.click()
            except Exception:
                print("✅ 더 이상 '다음' 버튼 없음 → 스토리 종료")
                break
            


        except Exception as e:
            print("❌ 스토리 순회 중 오류:", e)
            break

    return collected_links

def parse_posts(driver, links):
    for link in links:
        try:
            driver.get(link)
            time.sleep(3)

            spans = driver.find_elements(By.TAG_NAME, 'span')
            for span in spans:
                text = span.text
                if "그린의 제휴업체" in text and "제휴 혜택" in text:
                    restaurant_name = extract_restaurant_name(text)
                    benefit_text = extract_after(text, "제휴 혜택 :")
                    print("식당명:", restaurant_name)
                    print("제휴 혜택:", benefit_text)
                    print("---------------------------------------------------")
                    break
     
        except Exception as e:
            print(f"❌ 게시물 파싱 오류: {e}")

def extract_between(text, start, end):
    try:
        return text.split(start)[1].split(end)[0].strip()
    except IndexError:
        return "N/A"

def extract_after(text, keyword):
    try:
        return text.split(keyword)[1].split("\n")[0].strip()
    except IndexError:
        return "N/A"

def extract_restaurant_name(text):
    # '그린의 제휴업체 ' 또는 "그린의 제휴업체 " 이후, 따옴표 닫히기 전까지 추출
    match = re.search(r"그린의 제휴업체 ['\"](.*?)['\"].{1,2} 소개합니다", text)
    if match:
        return match.group(1).strip()
    return "N/A"
def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        login_instagram(driver)
        links = collect_links(driver, category)
        print(f"\n📦 총 수집된 게시물 링크 수: {len(links)}\n")
        parse_posts(driver, links)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()


