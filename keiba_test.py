import requests
import pandas as pd
from bs4 import BeautifulSoup

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
columns = ["着順","枠番","馬番","馬名","年齢","斤量","騎手","タイム","着差","タイム指数","通過","上り","単勝","人気","馬体重","調教タイム","厩舎コメント","備考","調教師","馬主","賞金"]
race_data_dict_list = []
soup = BeautifulSoup(response.text, 'html.parser')
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

Name_url = "https://db.netkeiba.com/jockey/00666/"
response_name = requests.get(Name_url,headers)
response_name.encoding = "EUC-JP"
Name_soup = BeautifulSoup(response_name.text, "html.parser")
Name_data = Name_soup.find('table',class_="ResultsByYears nk_tb_common race_table_01")
Name_dict_list = []
Rescolumns = ["年度","順位","１着","２着","３着","４着～","騎乗回数","重賞出走","重賞勝利","勝率","連対率","複勝率","代表馬"]
for x in Name_data.find_all("tr"):
    Result_data = []
    for Rcell in x.find_all("td"):
        Result_data.append(Rcell.text.strip())
    if Result_data:
        Result_dict = dict(zip(Rescolumns,Result_data))
        Name_dict_list.append(Result_dict)
Rdf = pd.DataFrame(Name_dict_list)
print(Rdf)



# ページのタイトルを取得して表示
# if soup.title:
#     print("取得したページのタイトル:")
#     print(soup.title.text)
# else:
#     print("エラー: ページのタイトルが見つかりませんでした。")