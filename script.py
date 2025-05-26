import os
import re
import time
import pymysql
import csv
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# .env 로드
load_dotenv()
INSTAGRAM_ID = os.getenv("INSTAGRAM_ID")
INSTAGRAM_PW = os.getenv("INSTAGRAM_PW")

TARGET_PROFILE = 'https://www.instagram.com/alliance.student.konkuk/'
CATEGORY = 8  # 7: 카페, 8: 음식점, 9: 호프

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

not_found_list = []


def login_instagram(driver):
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(3)
    driver.find_element(By.NAME, "username").send_keys(INSTAGRAM_ID)
    driver.find_element(By.NAME, "password").send_keys(INSTAGRAM_PW, Keys.RETURN)
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
    print("가게 개수:", len(story_slides))

    for _ in range(len(story_slides)):
        try:
            try:
                story_content = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[@role="button" and @style][contains(@style, "translate")]'))
                )
                ActionChains(driver).move_to_element(story_content).click().perform()
                time.sleep(2)
            except:
                pass
            # 게시물 보기 버튼 (팝업)
            post_btn = driver.find_elements(By.XPATH, '//div[@role="dialog"]//a[@role="link"]')
            if post_btn:
                href = post_btn[0].get_attribute("href")
                if href and href not in collected_links:
                    collected_links.append(href)
                    print(f"🔗 링크 수집됨: {href}")

            next_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div/div/div[3]/div/div/div[3]/div/section/div[1]/div/div[5]/div/div[2]/div[2]/div'))
            )
            next_btn.click()
            time.sleep(1)
        except Exception as e:
            print("✅ 스토리 종료 또는 오류:", e)
            break

    return collected_links


def parse_posts(driver, links):
    update_items = []
    for link in links:
        try:
            driver.get(link)
            time.sleep(3)
            spans = driver.find_elements(By.TAG_NAME, 'span')
            for span in spans:
                text = span.text
                if "그린의 제휴업체" in text and "제휴 혜택" in text:
                    name = extract_restaurant_name(text)
                    benefit = extract_after(text, "제휴 혜택 :")
                    if name != "N/A" and benefit != "N/A":
                        update_items.append((name, benefit))
                        print("식당명:", name)
                        print("제휴 혜택:", benefit)
                        print("---------------------------------------------------")
                    break
        except Exception as e:
            print(f"❌ 파싱 오류: {e}")
    return update_items


def extract_restaurant_name(text):
    match = re.search(r"그린의 제휴업체 ['\"](.*?)['\"].{1,2} 소개합니다", text)
    return match.group(1).strip() if match else "N/A"


def extract_after(text, keyword):
    match = re.search(rf"{re.escape(keyword)}\s*(.*?)\s*📍\s*위치", text, re.DOTALL)
    return match.group(1).strip() if match else "N/A"


def update_db_batch(conn, update_items):
    not_found = []
    updated_count = 0
    with conn.cursor() as cursor:
        for name, benefit in update_items:
            cursor.execute("SELECT COUNT(*) as cnt FROM restaurants_tbl WHERE restaurant_name = %s", (name,))
            count = cursor.fetchone()['cnt']
            if count == 1: # 이름 기준 1개인 식당만 업데이트
                cursor.execute("""
                    UPDATE restaurants_tbl
                    SET partnership_info = %s
                    WHERE restaurant_name = %s
                """, (benefit, name))
                updated_count += 1
                print(f"✅ 업데이트 완료: {name}")
            else:
                not_found.append((name, benefit))
    conn.commit()
    return updated_count, not_found


def save_not_found_list(not_found):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"restaurant_not_found_{timestamp}.csv"
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["restaurant_name", "benefit_info"])
        writer.writerows(not_found)
    print(f"📄 못 찾은 식당 저장 완료: {filename}")


def connect_to_db():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        conn = connect_to_db()
        login_instagram(driver)
        links = collect_links(driver, CATEGORY)
        print(f"\n🔗 수집된 링크 수: {len(links)}")
        updates = parse_posts(driver, links)
        print(f"\n🧾 파싱된 항목 수: {len(updates)}")
        updated_count, not_found = update_db_batch(conn, updates)
        print(f"\n실제 업데이트 완료 식당 수: {updated_count}")
        print(f"업데이트 실패한 식당 수: {len(not_found)}")

        if not_found:
            save_not_found_list(not_found)
    finally:
        driver.quit()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
