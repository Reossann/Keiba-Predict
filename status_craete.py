import requests
from selenium import webdriver
import pandas as pd
from bs4 import BeautifulSoup
import time
import re

all_jockey_df_list = []
url = 'https://race.netkeiba.com/race/result.html?race_id=202505021201&rf=race_list'

# ブラウザからのアクセスを偽装するための「名札」
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

page_jockeysURL = "https://race.netkeiba.com/top/race_list.html?kaisai_date=20250628"
Race_url_list = []

driver = webdriver.Chrome()
driver.get(page_jockeysURL)
print("ページを読み込んでいます...5秒待機します")
time.sleep(5)
html = driver.page_source
driver.quit()

Jsoup = BeautifulSoup(html, "html.parser")
weakjockey_table = Jsoup.find("div", class_="RaceList_Body RaceList_Top")
for row in weakjockey_table.find_all("li", class_="RaceList_DataItem hasMovieLink"):
    link_tag = row.find("a")
    if link_tag:
        relative_url = link_tag["href"]
        final_url = relative_url.replace("..","https://race.netkeiba.com")
        Race_url_list.append(final_url)

for URL in Race_url_list:
    driver = webdriver.Chrome() 
    driver.get(URL)
    print("ページを読み込んでいます...5秒待機します")
    time.sleep(5)
    html = driver.page_source
    driver.quit()
    columns = ["着順","枠番","馬番","馬名","年齢","斤量","騎手","タイム","着差","人気","単勝オッズ","後3F","コーナー通過順","厩舎","馬体重（増減）"]
    race_data_dict_list = []
    soup = BeautifulSoup(html, 'html.parser')
    race_info_text = soup.find("div",class_='RaceData01').text
    #距離
    distance_match = re.search(r'(\d+)m', race_info_text)
    distance = int(distance_match.group(1)) if distance_match else None
    #種類
    course_type = '芝' if '芝' in race_info_text else 'ダート'
    # 天候を抽出
    weather_match = re.search(r"天候\s*:\s*(\S+)", race_info_text)
    weather = weather_match.group(1) if weather_match else None
    # 馬場状態を抽出
    track_match = re.search(r"馬場\s*:\s*(\S+)", race_info_text)
    track_condition = track_match.group(1) if track_match else None
    all_data = soup.find("table",class_="RaceTable01 RaceCommon_Table ResultRefund Table_Show_All")
    for i in all_data.find_all("tr"):
        horse_data = []
        for cell in i.find_all("td"):
            horse_data.append(cell.text.strip())
        if horse_data:
            horse_dict = dict(zip(columns,horse_data))
            race_data_dict_list.append(horse_dict)
    Race_data_df = pd.DataFrame(race_data_dict_list)
    Race_data_df['着順'] = pd.to_numeric(Race_data_df['着順'], errors='coerce')
    # 新しい'is_top3'列を作成。着順が3以下の場合は1、それ以外は0にする
    Race_data_df['is_top3'] = Race_data_df['着順'].apply(lambda x: 1 if x <= 3 else 0)
    Race_data_df['距離'] = distance
    Race_data_df['種類'] = course_type
    Race_data_df["天候"] = weather
    Race_data_df["馬場"] = track_condition
    all_jockey_df_list.append(Race_data_df)



master_df = pd.concat(all_jockey_df_list)
master_df.to_csv('Datacsv/Race_database_2025_6_28.csv', index=False, encoding='utf-8-sig')
print("全騎手のデータベースが完成しました！")
print(master_df)



