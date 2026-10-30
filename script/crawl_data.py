import os
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from github import Github

# Tài khoản trường
USERNAME = os.environ["HUST_USERNAME"]
PASSWORD = os.environ["HUST_PASSWORD"]

# Cấu hình GitHub đích (Repo B)
GH_PAT = os.environ["GH_PAT"]
TARGET_REPO_NAME = "thanhlam0822/hust-master-tracker"
TARGET_FILE_PATH = "public/data.json" # Đường dẫn file trong Repo B

# URL
LOGIN_URL = "https://dkhsdh.hust.edu.vn/Account/login.aspx"
RESULTS_URL = "https://dkhsdh.hust.edu.vn/Student/StudentMark.aspx"

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('window-size=1920x1080')
    chrome_options.add_argument('--ignore-certificate-errors')
    return webdriver.Chrome(options=chrome_options)

def push_to_remote_repo(json_content):
    try:
        # Login bằng PAT
        g = Github(GH_PAT)
        # Lấy Repo B
        repo = g.get_repo(TARGET_REPO_NAME)

        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        commit_msg = f"🤖 Bot Update: Cập nhật điểm ngày {now}"

        try:
            # Tìm file cũ để lấy SHA (ID file)
            contents = repo.get_contents(TARGET_FILE_PATH)
            # Update (Ghi đè)
            repo.update_file(contents.path, commit_msg, json_content, contents.sha)
            print(f"✅ Đã UPDATE file sang repo {TARGET_REPO_NAME} thành công!")
        except:
            # Nếu chưa có thì tạo mới
            repo.create_file(TARGET_FILE_PATH, commit_msg, json_content)
            print(f"✅ Đã TẠO MỚI file bên repo {TARGET_REPO_NAME} thành công!")

    except Exception as e:
        print(f"❌ Lỗi khi đẩy sang Repo B: {e}")
        exit(1)

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

            header_idx = -1
            for idx, row in grade_table.iterrows():
                row_str = " ".join(row.astype(str).values)
                if 'Mã học phần' in row_str:
                    header_idx = idx
                    break

            if header_idx != -1:
                grade_table.columns = grade_table.iloc[header_idx]
                grade_table = grade_table.iloc[header_idx+1:].reset_index(drop=True)

            rename_map = {
                'Mã học phần': 'code',
                'Tên học phần': 'name',
                'Số TC': 'credits',
                'Quá trình': 'process_point',
                'Thi': 'exam_point',
                'TKHP': 'final_score'
                'Điểm chữ': 'letter_score',
            }
            available_cols = [c for c in rename_map.keys() if c in grade_table.columns]
            clean_df = grade_table[available_cols].rename(columns=rename_map)
            clean_df = clean_df.fillna("")

            json_str = clean_df.to_json(orient='records', force_ascii=False, indent=2)

            print(f"3. ☁️ Tìm thấy {len(clean_df)} môn. Đang đẩy sang Repo B...")
            push_to_remote_repo(json_str)

        else:
            print("❌ Không thấy bảng dữ liệu.")
            exit(1)

    except Exception as e:
        print(f"❌ Lỗi: {e}")
        exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_crawler()