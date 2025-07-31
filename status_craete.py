import os
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import numpy as np
import requests

def get_horse_status(horse_url):
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
    response = requests.get(horse_url,headers=headers)
    response.encoding = 'EUC-JP'
    html_text = response.text
    soup = BeautifulSoup(html_text,"html.parser")
    table = soup.find("table",class_="db_h_race_results nk_tb_common")
    tbody = table.find("tbody")
    for _ in range(3):
        tr = tbody.find("tr")
    



# --- 1. 初期設定 ---
# 開催日を指定
kaisai_date = "20250706"
# その日のレース一覧ページURL
race_list_url = f"https://race.netkeiba.com/top/race_list.html?kaisai_date={kaisai_date}"
# 保存先フォルダ
output_dir = 'Datacsv'
# 保存ファイル名
output_file = f'Race_database_{kaisai_date}.parquet'

# Seleniumを効率化するための設定
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_experimental_option("prefs", {"profile.default_content_setting_values.images": 2})

# --- 2. その日の全レースURLを取得 ---
print(f"{kaisai_date} の全レースURLを取得中...")
race_url_list = []
driver = webdriver.Chrome(options=options)
try:
    driver.get(race_list_url)
    # リンク要素が見つかるまで最大10秒待機
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "RaceList_DataItem"))
    )
    # RaceList_DataItemクラスを持つli要素の中のaタグを取得
    race_links = driver.find_elements(By.CSS_SELECTOR, "li.RaceList_DataItem a")
    for link in race_links:
        href = link.get_attribute('href')
        if href and "race_id" in href:
            # resultページへのURLに整形
            race_id = re.search(r'race_id=(\w+)', href).group(1)
            full_url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"
            race_url_list.append(full_url)
finally:
    driver.quit()

# 重複を削除
unique_race_urls = sorted(list(set(race_url_list)))
print(f"{len(unique_race_urls)}件のユニークなレースURLを見つけました。")

# --- 3. 各レースの詳細データをスクレイピング ---
all_race_df_list = []
print("各レースの詳細データ収集中...")

# メインのスクレイピングのためにブラウザを一度だけ起動
driver = webdriver.Chrome(options=options)
try:
    for url in unique_race_urls:
        try:
            print(f"処理中: {url}")
            driver.get(url)
            # レース結果テーブルが表示されるまで最大10秒待機
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "RaceTable01"))
            )
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # --- コース情報の抽出 ---
            race_info_text = soup.find('div', class_='RaceData01').text
            distance_match = re.search(r'(\d+)m', race_info_text)
            distance = int(distance_match.group(1)) if distance_match else None
            course_type = '芝' if '芝' in race_info_text else 'ダート'
            weather_match = re.search(r"天候\s*:\s*(\S+)", race_info_text)
            weather = weather_match.group(1) if weather_match else None
            track_match = re.search(r"馬場\s*:\s*(\S+)", race_info_text)
            track_condition = track_match.group(1) if track_match else None


            # --- レース結果テーブルの抽出 ---
            table = soup.find("table", class_="RaceTable01")
            columns = ["着順","枠番","馬番","馬名","年齢","斤量","騎手","タイム","着差","人気","単勝オッズ","後3F","コーナー通過順","厩舎","馬体重(増減)"]
            
            race_data_dict_list = []
            # ヘッダー行(tr)を除外するために[1:]でスライス
            for row in table.find_all("tr")[1:]:
                    row_data = [] # 馬一頭分のデータを格納する空のリスト
                    horse_url = None # 馬のURLを格納する変数を初期化
                    # enumerateを使って、セルのインデックス番号(i)と中身(cell)を同時に取得
                    for i, cell in enumerate(row.find_all("td")):
                        # もし、4番目(インデックス3)のセル、つまり馬名のセルだったら
                        if i == 3:
                            # <a>タグを探し、href属性を取得する
                            link_tag = cell.find('a')
                            if link_tag:
                                horse_url = link_tag['href']
                                # 馬名のテキストも取得しておく
                                row_data.append(cell.text.strip())
                        else:
                            # 馬名以外のセルは、通常通りテキストだけを取得
                            row_data.append(cell.text.strip())
                    # ループが終わった後、データが完全かチェック
                    if len(row_data) == len(columns):
                        # 辞書を作成
                        horse_dict = dict(zip(columns, row_data))
                        # 取得した馬のURLも辞書に追加
                        horse_dict['馬URL'] = horse_url
                        # 最終的なリストに辞書を追加
                        race_data_dict_list.append(horse_dict)  

            if race_data_dict_list:
                race_df = pd.DataFrame(race_data_dict_list)
                # コース情報などを新しい列として追加
                race_df['着順'] = pd.to_numeric(race_df['着順'], errors='coerce')
                # np.where()を使って新しい列を作成
                race_df['is_top3'] = np.where(race_df['着順'] <= 3, 1, 0)
                race_df['距離'] = distance
                race_df['種類'] = course_type
                race_df["天候"] = weather
                race_df["馬場"] = track_condition
                all_race_df_list.append(race_df)

        except Exception as e:
            print(f"エラーが発生しました: {url}, {e}")
            continue
finally:
    driver.quit()

# --- 4. データの結合と保存 ---
if all_race_df_list:
    master_df = pd.concat(all_race_df_list, ignore_index=True)

    # フォルダが存在しなければ作成
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    full_path = os.path.join(output_dir, output_file)
    master_df.to_parquet(full_path, index=False)

    print("-" * 50)
    print(f"全レースのデータベースが完成しました！")
    print(f"ファイルは '{full_path}' に保存されました。")
    print(f"合計 {len(master_df)} 件のデータを取得しました。")
else:
    print("収集できるデータがありませんでした。")