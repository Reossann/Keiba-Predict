import pandas as pd
import joblib
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import re
import numpy as np
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PROJECT_ROOT = Path(__file__).resolve().parent

# --- ヘルパー関数の定義 (データ収集時と全く同じもの) ---
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
        # サーバーへの配慮
        time.sleep(1)
        driver.get(horse_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.db_h_race_results"))
        )
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        table = soup.find("table", class_="db_h_race_results")
        if not table or not table.find("tbody"): return None

        past_results = []
        columns = ["日付","開催","天気","R","レース名","映像","頭数","枠番","馬番","オッズ","人気","着順","騎手","斤量","距離","馬場","馬場指数","タイム","着差","タイム指数","通過","ペース","上り","馬体重","厩舎ｺﾒﾝﾄ","備考","勝ち馬","賞金"]
        
        for row in table.find("tbody").find_all("tr")[:3]:
            row_data = [td.text.strip() for td in row.find_all("td")]
            if len(row_data) == len(columns) + 1: row_data = row_data[1:]
            if len(row_data) == len(columns):
                past_results.append(dict(zip(columns, row_data)))
        
        return pd.DataFrame(past_results) if past_results else None
    except Exception as e:
        print(f"  過去成績の取得中にエラー: {horse_url}, {e}")
        return None

# --- 1. モデルとエンコーダの読み込み ---
print("学習済みモデルとエンコーダを読み込んでいます...")
try:
    encoders = joblib.load(PROJECT_ROOT / 'encoders.joblib')
    model = joblib.load(PROJECT_ROOT / 'lgbm_model.joblib')
    print("読み込み完了。")
except FileNotFoundError:
    print("エラー: 'encoders.joblib' または 'lgbm_model.joblib' が見つかりません。")
    print("先に 'train_model.py' を実行して、モデルを学習・保存してください。")
    exit()

# --- 2. 予測したいレースのデータを取得 ---
URL = input("予想したいレースの出走馬表URLを入力してください: ")

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_experimental_option("prefs", {"profile.default_content_setting_values.images": 2})

driver = webdriver.Chrome(options=options)
print("レースデータを取得中...")
new_df = pd.DataFrame() # 空のDataFrameを準備
try:
    driver.get(URL)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "Shutuba_Table")))
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    race_info_text = soup.find('div', class_='RaceData01').text
    distance = int(re.search(r'(\d+)m', race_info_text).group(1))
    course_type = '芝' if '芝' in race_info_text else 'ダート'
    weather_match = re.search(r"天候\s*:\s*(\S+)", race_info_text)
    weather = weather_match.group(1) if weather_match else 'unknown'
    track_match = re.search(r"馬場\s*:\s*(\S+)", race_info_text)
    track_condition = track_match.group(1) if track_match else 'unknown'

    table = soup.find("table", class_="Shutuba_Table")
    #【修正点】出馬表に合わせた正しい列名リスト
    columns = ["枠", "馬番", "印", "馬名", "性齢", "斤量", "騎手", "厩舎", "馬体重(増減)", "オッズ", "人気","","","",""]
    
    race_data_list = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
    #     print(f"--- 1行分の全セルデータ（合計: {len(cells)}個） ---")
    
    # # enumerateを使って、各セルのインデックス番号と中身を全て表示する
    #     for i, cell in enumerate(cells):
    #         print(f"[{i}番目]: {cell.text.strip()}")
        
    #     print("-" * 30)
        #【修正点】出馬表の列数でチェック
        if len(cells) == len(columns):
            row_data = [cell.text.strip() for cell in cells]
            horse_dict = dict(zip(columns, row_data))
            
            horse_url_tag = cells[3].find('a')
            horse_dict['馬詳細URL'] = horse_url_tag['href'] if horse_url_tag else None
            race_data_list.append(horse_dict)
    
    new_df = pd.DataFrame(race_data_list)
    new_df['距離'] = distance
    new_df['種類'] = course_type
    new_df["天候"] = weather
    new_df["馬場"] = track_condition

    # --- 3. 過去成績を取得し、特徴量を作成 ---
    print("各馬の過去成績を取得し、特徴量を計算中...")
    all_past_results = []
    for index, row in new_df.iterrows():
        if row['馬詳細URL']:
            past_df = get_horse_past_results(row['馬詳細URL'], driver)
            if past_df is not None:
                past_df['馬名'] = row['馬名']
                all_past_results.append(past_df)
    
    if all_past_results:
        past_df_combined = pd.concat(all_past_results, ignore_index=True)
        numeric_cols_past = ['着順', '上り', '人気', 'オッズ', 'タイム']
        for col in numeric_cols_past:
            past_df_combined[col] = pd.to_numeric(past_df_combined[col], errors='coerce')
        past_df_combined['タイム(秒)'] = past_df_combined['タイム'].apply(time_to_seconds)
        past_df_cleaned = past_df_combined.dropna(subset=numeric_cols_past + ['タイム(秒)'])

        last_3_races = past_df_cleaned.groupby('馬名').head(3)
        agg_dict = {'着順': 'mean','上り': 'mean','人気': 'mean','オッズ': 'mean','タイム(秒)': 'mean'}
        past_features = last_3_races.groupby('馬名').agg(agg_dict).reset_index()
        past_features = past_features.rename(columns={
            '着順': '過去3走平均着順','上り': '過去3走平均上り','人気': '過去3走平均人気',
            'オッズ': '過去3走平均オッズ','タイム(秒)': '過去3走平均タイム'
        })
        new_df = pd.merge(new_df, past_features, on='馬名', how='left')

finally:
    driver.quit()

# --- 4. 学習時と同じ形式にデータを加工 ---
if not new_df.empty:
    print("最終データ加工中...")
    categorical_cols = ['騎手', '馬名', '厩舎', '性齢', '天候', '馬場', '種類']
    for col in categorical_cols:
        encoder = encoders.get(col)
        if encoder and col in new_df.columns:
            new_df[col] = new_df[col].fillna('unknown')
            known_labels = list(encoder.classes_)
            new_df[col + '_enc'] = new_df[col].apply(lambda x: encoder.transform([x])[0] if x in known_labels else -1)

    numeric_cols = ['斤量', '距離', '人気', 'オッズ', '過去3走平均着順', '過去3走平均上り', '過去3走平均人気', '過去3走平均オッズ', '過去3走平均タイム']
    for col in numeric_cols:
        if col in new_df.columns:
            new_df[col] = pd.to_numeric(new_df[col], errors='coerce')

    new_df.fillna(0, inplace=True)

    # --- 5. 予測の実行 ---
    train_feature_names = model.booster_.feature_name()
    for col in train_feature_names:
        if col not in new_df.columns:
            new_df[col] = 0
    X_pred = new_df[train_feature_names]

    print("AIによる予測を実行中...")
    pred_proba = model.predict_proba(X_pred)[:, 1]
    new_df['予測確率'] = pred_proba

    # --- 6. 結果の表示 ---
    result_df = new_df[['馬番', '馬名', '騎手', 'オッズ', '人気', '予測確率']]
    sorted_result = result_df.sort_values(by='予測確率', ascending=False).reset_index(drop=True)
    sorted_result.index = sorted_result.index + 1

    print("\n--- AIによる競馬予想結果 ---")
    print(sorted_result)
else:
    print("出走馬データの取得に失敗しました。")