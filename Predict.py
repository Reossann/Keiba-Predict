import joblib
import pandas as pd
import requests
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import re

# 1. 保存したエンコーダとモデルを読み込む
encoders = joblib.load('encoders.joblib')
model = joblib.load('lgbm_model.joblib')

URL = input("予想したいレースのURLを入力してください:")

# 2. 新しいレースデータを取得
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
all_data = soup.find("table",class_="Shutuba_Table RaceTable01 ShutubaTable tablesorter tablesorter-default")
for i in all_data.find_all("tr"):
    horse_data = []
    for cell in i.find_all("td"):
        horse_data.append(cell.text.strip())
    if horse_data:
        horse_dict = dict(zip(columns,horse_data))
        race_data_dict_list.append(horse_dict)
new_df = pd.DataFrame(race_data_dict_list)
new_df['距離'] = distance
new_df['種類'] = course_type
new_df["天候"] = weather
new_df["馬場"] = track_condition


# 1. 学習時と「同じ」カテゴリ列と数値列を定義
categorical_cols = ['騎手', '馬名', '厩舎', '年齢', '天候', '馬場', '種類']
numeric_cols = ['斤量', '距離']

# 2. カテゴリ列を、保存したエンコーダで変換
for col in categorical_cols:
    encoder = encoders.get(col) # 辞書からエンコーダを取得
    if encoder:
        known_labels = list(encoder.classes_)
        new_df[col + '_enc'] = new_df[col].apply(lambda x: encoder.transform([x])[0] if x in known_labels else -1)

# 3. 数値列を、数値型に変換
for col in numeric_cols:
    new_df[col] = pd.to_numeric(new_df[col], errors='coerce')

# 4. NaNを処理（学習時と同じ方法で）
#    ここでは0で埋める例。学習時に平均値で埋めたなら、その方法に合わせる。
new_df = new_df.fillna(0)

# 5. 学習時と「全く同じ」特徴量リストを作成
feature_columns = [col + "_enc" for col in categorical_cols] + numeric_cols
X_pred = new_df[feature_columns]
pred_proba = model.predict_proba(X_pred)[:, 1]
# 3. 予測結果を元のDataFrameに追加
new_df['予測確率'] = pred_proba

# 4. 必要な列だけを選び、確率が高い順に並び替える
result_df = new_df[['馬名', '騎手', '予測確率']]
sorted_result = result_df.sort_values(by='予測確率', ascending=False)
sorted_result.index = sorted_result.index + 1

# 5. 最終的な予想結果を表示
print("--- AIによる競馬予想結果 ---")
print(sorted_result)



