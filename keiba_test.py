import requests
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
soup = BeautifulSoup(response.text, 'html.parser')

# ページのタイトルを取得して表示
if soup.title:
    print("取得したページのタイトル:")
    print(soup.title.text)
else:
    print("エラー: ページのタイトルが見つかりませんでした。")