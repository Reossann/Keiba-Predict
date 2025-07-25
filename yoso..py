import requests
from selenium import webdriver
import pandas as pd
from bs4 import BeautifulSoup
import time
import re

#すべての情報を格納するリスト
all_jockey_df_list = []
Rescolumns = ["年度","順位","１着","２着","３着","４着～","騎乗回数","重賞出走","重賞勝利","勝率","連対率","複勝率","代表馬"]
# 2025年7/26の日本ダービーのURL
url = 'https://race.netkeiba.com/race/shutuba.html?race_id=202504020106&rf=race_submenu'

# ブラウザからのアクセスを偽装するための「名札」
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

driver = webdriver.Chrome()
driver.get(url)
print("ページを読み込んでいます...5秒待機します")
time.sleep(5)
html = driver.page_source
driver.quit()

columns = ["枠番","馬番","印","馬名","年齢","斤量","騎手名","宿主","馬体重","オッズ","人気"]
race_data_dict_list = []
soup = BeautifulSoup(html, 'html.parser')
all_data = soup.find("table", class_="Shutuba_Table RaceTable01 ShutubaTable tablesorter tablesorter-default")
for i in all_data.find_all("tr"):
    horse_data = []
    for cell in i.find_all("td"):
        horse_data.append(cell.text.strip())
    if horse_data:
        horse_dict = dict(zip(columns,horse_data))
        race_data_dict_list.append(horse_dict)

df = pd.DataFrame(race_data_dict_list)



jockey_db = pd.read_csv("jockey_database.csv")
jockey_db_total = jockey_db[jockey_db['年度'] == '2025']
jockey_db_total = jockey_db_total.rename(columns={
    '勝率': '騎手勝率',
    '連対率': '騎手連対率',
    '複勝率': '騎手複勝率'
})
jockey_db_total['騎手複勝率'] = jockey_db_total['騎手複勝率'].str.replace('％', '').astype(float)
jockey_db_total['Score'] = jockey_db_total['騎手複勝率']
jockey_db_total["名字"] = jockey_db_total["騎手名"].str[:2]

Marge_pd = pd.merge(df,jockey_db_total,left_on="騎手名",right_on="名字",how="left")

final_columns = ['馬番', '馬名', '騎手名_x', 'Score', "人気"]

# 元のDataFrameから、必要な列だけを選んで新しいDataFrameを作成
final_df = Marge_pd[final_columns]
final_df['Score'] = final_df['Score'].fillna(0)
final_df_sorted = final_df.sort_values(by='Score', ascending=False)
print(final_df_sorted)
