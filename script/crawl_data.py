import os
import time
import pandas as pd
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ================= CẤU HÌNH (LẤY TỪ BIẾN MÔI TRƯỜNG) =================
# Không điền user/pass trực tiếp vào đây để bảo mật
USERNAME = os.environ["HUST_USERNAME"]
PASSWORD = os.environ["HUST_PASSWORD"]
LOGIN_URL = "https://dkhsdh.hust.edu.vn/Account/login.aspx"
RESULTS_URL = "https://dkhsdh.hust.edu.vn/StudyRegister/RegistrationHistory.aspx"
OUTPUT_FILE = "public/data.json"

# ================= SETUP CHROME =================
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless') # Bắt buộc trên GitHub Actions
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('window-size=1920x1080')
    chrome_options.add_argument('--ignore-certificate-errors')
    return webdriver.Chrome(options=chrome_options)

# ================= CHẠY CRAWLER =================
def run_crawler():
    driver = get_driver()
    try:
        print("1. 🚀 Login HUST...")
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 10)

        driver.find_element(By.ID, "Username").send_keys(USERNAME)
        driver.find_element(By.ID, "Password").send_keys(PASSWORD)
        driver.find_element(By.ID, "btnSignIn").click()
        time.sleep(5)

        print("2. 🔗 Lấy dữ liệu...")
        driver.get(RESULTS_URL)
        time.sleep(5)

        dfs = pd.read_html(driver.page_source)

        if len(dfs) > 0:
            grade_table = max(dfs, key=len)

            # --- XỬ LÝ DỮ LIỆU ---
            # 1. Tìm header chuẩn
            header_idx = -1
            for idx, row in grade_table.iterrows():
                row_str = " ".join(row.astype(str).values)
                if 'Mã học phần' in row_str:
                    header_idx = idx
                    break

            if header_idx != -1:
                grade_table.columns = grade_table.iloc[header_idx]
                grade_table = grade_table.iloc[header_idx+1:].reset_index(drop=True)

            # 2. Map tên tiếng Anh
            rename_map = {
                'Mã học phần': 'code',
                'Tên học phần': 'name',
                'TC': 'credits',
                'Học kỳ': 'semester',
                'Ngày giờ đăng ký': 'date'
            }

            available_cols = [c for c in rename_map.keys() if c in grade_table.columns]
            clean_df = grade_table[available_cols].rename(columns=rename_map)
            clean_df = clean_df.fillna("")

            # 3. Lưu ra file JSON
            # Lưu ý: Script này chỉ ghi file ra đĩa, việc push lên git do Workflow lo
            os.makedirs("public", exist_ok=True)
            clean_df.to_json(OUTPUT_FILE, orient='records', force_ascii=False, indent=2)

            print(f"✅ Đã lưu {len(clean_df)} dòng vào {OUTPUT_FILE}")

        else:
            print("❌ Không thấy bảng dữ liệu.")
            exit(1) # Báo lỗi để workflow biết

    except Exception as e:
        print(f"❌ Lỗi: {e}")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_crawler()