import os
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import date, timedelta
import numpy as np
import random

# --- 1. ヘルパー関数の定義 ---

def time_to_seconds(time_str):
    """タイム文字列（例: "1:33.5"）を秒数（例: 93.5）に変換する関数"""
    try:
        parts = time_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except (ValueError, AttributeError):
        return None

def get_horse_past_results(horse_url, driver):
    """馬のURLと共有driverを受け取り、過去3走の成績をDataFrameとして返す関数"""
    try:
        driver.get(horse_url)
        WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.db_h_race_results"))
        )
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        table = soup.find("table", class_="db_h_race_results")
        if not table or not table.find("tbody"):
            return None

        past_results = []
        # 実際のテーブルに合わせて列を調整
        columns = ["日付","開催","天気","R","レース名","映像","頭数","枠番","馬番","オッズ","人気","着順","騎手","斤量","距離","馬場","馬場指数","タイム","着差","タイム指数","通過","ペース","上り","馬体重","厩舎ｺﾒﾝﾄ","備考","勝ち馬","賞金"]
        
        for row in table.find("tbody").find_all("tr")[:3]:
            row_data = [td.text.strip() for td in row.find_all("td")]
            # 予想印の空白列（1列目）を除外
            if len(row_data) == len(columns) + 1:
                 row_data = row_data[1:]

            if len(row_data) == len(columns):
                past_results.append(dict(zip(columns, row_data)))
        
        return pd.DataFrame(past_results) if past_results else None

    except Exception as e:
        print(f"  過去成績の取得中にエラー: {horse_url}, {e}")
        return None

# --- 2. 初期設定 ---
output_dir = 'Database'
output_file = 'race_database_with_features.parquet'
days_to_scrape = 365 # 過去何日分を収集するか

# --- 3. 過去1年分の日付リスト作成 ---
date_list = [
    (date.today() - timedelta(days=i)).strftime("%Y%m%d") 
    for i in range(days_to_scrape)
]
print(f"収集対象期間: {len(date_list)}日分")

# --- 4. 全レースURLの取得 ---
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_experimental_option("prefs", {"profile.default_content_setting_values.images": 2})

all_race_urls = []
driver = webdriver.Chrome(options=options)
try:
    for kaisai_date in date_list:
        try:
            time.sleep(random.uniform(1, 2)) # サーバーへの配慮
            
            race_list_url = f"https://race.netkeiba.com/top/race_list.html?kaisai_date={kaisai_date}"
            driver.get(race_list_url)
            WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.CLASS_NAME, "RaceList_DataItem")))
            
            race_links = driver.find_elements(By.CSS_SELECTOR, "li.RaceList_DataItem a")
            for link in race_links:
                href = link.get_attribute('href')
                if href and "race_id" in href:
                    race_id = re.search(r'race_id=(\w+)', href).group(1)
                    all_race_urls.append(f"https://race.netkeiba.com/race/result.html?race_id={race_id}")
            print(f"{kaisai_date}: URL取得完了")
        except Exception:
            print(f"{kaisai_date}: レース開催なし")
            continue
finally:
    driver.quit()

unique_race_urls = sorted(list(set(all_race_urls)))
print(f"\n合計 {len(unique_race_urls)} 件のレースURLを取得しました。")

# --- 5. メインのスクレイピング処理 ---
all_races_data = []
all_past_results_data = []
driver = None

try:
    for i, url in enumerate(unique_race_urls):
        if i % 100 == 0:
            if driver:
                driver.quit()
            print(f"--- ブラウザを再起動 ({i}/{len(unique_race_urls)}) ---")
            driver = webdriver.Chrome(options=options)

        try:
            print(f"処理中: {url}")
            driver.get(url)
            WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.CLASS_NAME, "RaceTable01")))
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            race_info_text = soup.find('div', class_='RaceData01').text
            distance_match = re.search(r'(\d+)m', race_info_text)
            distance = int(distance_match.group(1)) if distance_match else None
            course_type = '芝' if '芝' in race_info_text else 'ダート'
            weather_match = re.search(r"天候\s*:\s*(\S+)", race_info_text)
            weather = weather_match.group(1) if weather_match else None
            track_match = re.search(r"馬場\s*:\s*(\S+)", race_info_text)
            track_condition = track_match.group(1) if track_match else None
            
            table = soup.find("table", class_="RaceTable01")
            columns = ["着順","枠番","馬番","馬名","性齢","斤量","騎手","タイム","着差","人気","オッズ","後3F","コーナー通過順","厩舎","馬体重(増減)"]
            
            for row in table.find_all("tr")[1:]:
                cells = row.find_all("td")
                horse_url_tag = cells[3].find('a')
                if horse_url_tag and len(cells) == len(columns):
                    horse_url = horse_url_tag['href']
                    row_data = [cell.text.strip() for cell in cells]
                    row_dict = dict(zip(columns, row_data))
                    row_dict.update({'距離': distance, '種類': course_type, '天候': weather, '馬場': track_condition, '馬URL': horse_url, 'レースURL': url})
                    all_races_data.append(row_dict)
                    
                    past_df = get_horse_past_results(horse_url, driver)
                    if past_df is not None:
                        past_df['馬名'] = row_dict['馬名']
                        all_past_results_data.append(past_df)
            
            time.sleep(random.uniform(1, 2))

        except Exception as e:
            print(f"  詳細データ取得中にエラー: {url}, {e}")
            continue
finally:
    if driver:
        driver.quit()

# --- 6. 特徴量作成と結合 ---
if all_races_data and all_past_results_data:
    main_df = pd.DataFrame(all_races_data)
    past_df = pd.concat(all_past_results_data, ignore_index=True)

    numeric_cols = ['着順', '上り', '人気', 'オッズ', 'タイム']
    for col in numeric_cols:
        past_df[col] = pd.to_numeric(past_df[col], errors='coerce')
    past_df['タイム(秒)'] = past_df['タイム'].apply(time_to_seconds)
    past_df_cleaned = past_df.dropna(subset=numeric_cols + ['タイム(秒)'])

    last_3_races = past_df_cleaned.groupby('馬名').head(3)
    agg_dict = {'着順': 'mean', '上り': 'mean', '人気': 'mean', 'オッズ': 'mean', 'タイム(秒)': 'mean'}
    past_features = last_3_races.groupby('馬名').agg(agg_dict).reset_index()
    past_features = past_features.rename(columns={
        '着順': '過去3走平均着順', '上り': '過去3走平均上り', '人気': '過去3走平均人気',
        'オッズ': '過去3走平均オッズ', 'タイム(秒)': '過去3走平均タイム'
    })

    final_df = pd.merge(main_df, past_features, on='馬名', how='left')

    # --- 7. 保存 ---
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    full_path = os.path.join(output_dir, output_file)
    final_df.to_parquet(full_path, index=False)
    
    print("-" * 50)
    print(f"データベースが完成しました！ '{full_path}' に保存されました。")
    print(f"合計 {len(final_df)} 件のデータを取得しました。")
else:
    print("収集できるデータがありませんでした。")