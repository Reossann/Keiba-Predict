import requests
from selenium import webdriver
import pandas as pd
from bs4 import BeautifulSoup
import time
import re

url = 'https://db.netkeiba.com/race/202506020811/'

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

columns = ["着順","枠番","馬番","馬名","年齢","斤量","騎手","タイム","着差","タイム指数","通過","上り","単勝","人気","馬体重","調教タイム","厩舎コメント","備考","調教師","馬主","賞金"]
race_data_dict_list = []
soup = BeautifulSoup(html, 'html.parser')
all_data = soup.find("table",class_="race_table_01 nk_tb_common")
for i in all_data.find_all("tr"):
    horse_data = []
    for cell in i.find_all("td"):
        horse_data.append(cell.text.strip())
    if horse_data:
        horse_dict = dict(zip(columns,horse_data))
        race_data_dict_list.append(horse_dict)

df = pd.DataFrame(race_data_dict_list)
print(df)