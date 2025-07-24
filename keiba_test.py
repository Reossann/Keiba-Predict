import requests
from selenium import webdriver
import pandas as pd
from bs4 import BeautifulSoup
import time
import re

#すべての情報を格納するリスト
all_jockey_df_list = []
Rescolumns = ["年度","順位","１着","２着","３着","４着～","騎乗回数","重賞出走","重賞勝利","勝率","連対率","複勝率","代表馬"]
# 2024年の日本ダービーのURL
url = 'https://db.netkeiba.com/race/202405030812/'

# ブラウザからのアクセスを偽装するための「名札」
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 「名札」を付けてURLにアクセスしHTMLを取得
response = requests.get(url, headers=headers)

# 文字化けを防ぐためにエンコーディングを設定
response.encoding = 'EUC-JP'

# HTMLを解析
# !レース情報がほとんど乗っているやつを作成
# columns = ["着順","枠番","馬番","馬名","年齢","斤量","騎手","タイム","着差","タイム指数","通過","上り","単勝","人気","馬体重","調教タイム","厩舎コメント","備考","調教師","馬主","賞金"]
# race_data_dict_list = []
# soup = BeautifulSoup(response.text, 'html.parser')
# all_data = soup.find("table",class_="race_table_01 nk_tb_common")
# for i in all_data.find_all("tr"):
#     horse_data = []
#     for cell in i.find_all("td"):
#         horse_data.append(cell.text.strip())
#     if horse_data:
#         horse_dict = dict(zip(columns,horse_data))
#         race_data_dict_list.append(horse_dict)

# df = pd.DataFrame(race_data_dict_list)
# print(df)
page_jockeysURL = "https://race.netkeiba.com/race/search.html?kaisai_date=20250726&current_group=1020250726&mode=jockey"
jockey_url_list = []

driver = webdriver.Chrome()
driver.get(page_jockeysURL)
print("ページを読み込んでいます...5秒待機します")
time.sleep(5)
html = driver.page_source
driver.quit()

Jsoup = BeautifulSoup(html, "html.parser")
weakjockey_table = Jsoup.find("table", class_="ThisWeek_List_Table Table_jockey")
for row in weakjockey_table.find_all("tr"):
    link_tag = row.find("a")
    if link_tag:
        relative_url = link_tag["href"]
        full_url = re.sub(r"/thisweek","",relative_url)
        jockey_url_list.append(full_url)


for Name_url in jockey_url_list:
    response_name = requests.get(Name_url,headers)
    response_name.encoding = "EUC-JP"
    Name_soup = BeautifulSoup(response_name.text, "html.parser")
    Name_data = Name_soup.find('table',class_="ResultsByYears nk_tb_common race_table_01")
    title_text = Name_soup.find("title").text
    jockey_name = title_text.replace("のプロフィール | 騎手データ - netkeiba", "").strip()
    for x in Name_data.find_all("tr"):
        Result_data = []
        for Rcell in x.find_all("td"):
            Result_data.append(Rcell.text.strip())
        if len(Result_data)== len(Rescolumns):
            Result_dict = dict(zip(Rescolumns,Result_data))
            Result_dict["騎手名"] = jockey_name
            all_jockey_df_list.append(Result_dict)
   

master_df = pd.DataFrame(all_jockey_df_list)
master_df.to_csv('jockey_database.csv', index=False, encoding='utf-8-sig')
print("全騎手のデータベースが完成しました！")
print(master_df)

#!一人一人のurlをいれたらその成績を軽く取得できるプログラム
# Name_url = "https://db.netkeiba.com/jockey/00666/"
# response_name = requests.get(Name_url,headers)
# response_name.encoding = "EUC-JP"
# Name_soup = BeautifulSoup(response_name.text, "html.parser")
# Name_data = Name_soup.find('table',class_="ResultsByYears nk_tb_common race_table_01")
# Name_dict_list = []
# Rescolumns = ["年度","順位","１着","２着","３着","４着～","騎乗回数","重賞出走","重賞勝利","勝率","連対率","複勝率","代表馬"]
# for x in Name_data.find_all("tr"):
#     Result_data = []
#     for Rcell in x.find_all("td"):
#         Result_data.append(Rcell.text.strip())
#     if Result_data:
#         Result_dict = dict(zip(Rescolumns,Result_data))
#         Name_dict_list.append(Result_dict)
# Rdf = pd.DataFrame(Name_dict_list)
# print(Rdf)



# ページのタイトルを取得して表示
# if soup.title:
#     print("取得したページのタイトル:")
#     print(soup.title.text)
# else:
#     print("エラー: ページのタイトルが見つかりませんでした。")