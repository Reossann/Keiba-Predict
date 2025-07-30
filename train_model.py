import pandas as pd
from sklearn.preprocessing  import LabelEncoder
from sklearn.model_selection import train_test_split
import lightgbm as lgb
from sklearn.metrics import accuracy_score, roc_auc_score
import matplotlib.pyplot as plt
import japanize_matplotlib # 日本語表示のためのライブラリ
import joblib
import glob

# 1. 保存したデータベースを読み込む
# この一行で、これまでの苦労の成果を瞬時に呼び出せる
path_dir = 'Datacsv'
# 1. CSVファイルのパスリストを取得
csv_files = glob.glob(f'{path_dir}/*.csv')

# 2. Parquetファイルのパスリストを取得
parquet_files = glob.glob(f'{path_dir}/*.parquet')

# 3. 2つのリストを結合
all_files = csv_files + parquet_files

print("見つかった全ファイル:", all_files)
df_list = []
for file in all_files:
    if file.endswith('.csv'):
        df_list.append(pd.read_csv(file))
    elif file.endswith('.parquet'):
        df_list.append(pd.read_parquet(file))
df = pd.concat(df_list, ignore_index=True)
encoders={}
# 2. エンコーディング処理を行う
# (ここに前回のヒントであるLabelEncoderのコードが入る)
# 1. カテゴリとしてエンコードしたい列
categorical_cols = ['騎手', '馬名', '厩舎', '年齢', '天候', '馬場', '種類']
for col in categorical_cols:
    le = LabelEncoder()
    # NaNを'unknown'などの文字列で埋めてからエンコードすると、より安定します
    df[col] = df[col].fillna('unknown')
    df[col + "_enc"] = le.fit_transform(df[col])
    encoders[col] = le

# 2. 数値として扱いたい列
#    (馬体重から増減を抜き出すなど、より高度な処理も可能)
numeric_cols = ['斤量', '距離']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# NaNの処理（ここでは平均値で埋めてみる例）
df = df.fillna(df.mean(numeric_only=True))

# 3. 最終的に学習に使う特徴量の列を定義
feature_columns = [col + "_enc" for col in categorical_cols] + numeric_cols
X = df[feature_columns]
y = df['is_top3']

# 2. データを学習用とテスト用に分割
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)


# 3. LightGBMモデルを準備し、学習させる
model = lgb.LGBMClassifier()
model.fit(X_train, y_train)
joblib.dump(model, 'lgbm_model.joblib')

print("モデルの学習が完了しました！")

# 1. テストデータを使って予測を実行
#    「1になる確率」だけを取り出す
y_pred_proba = model.predict_proba(X_test)[:, 1]

# 2. 確率を元に「0か1か」の予測も行う（閾値0.5の場合）
y_pred = (y_pred_proba > 0.5).astype(int)

# 3. 実際の答え(y_test)と予測結果(y_pred)を比較して精度を計算
accuracy = accuracy_score(y_test, y_pred)
roc_auc = roc_auc_score(y_test, y_pred_proba)

print(f"正解率 (Accuracy): {accuracy:.4f}")
print(f"ROC-AUCスコア: {roc_auc:.4f}")

# 特徴量の重要度をプロットする
lgb.plot_importance(model, figsize=(12, 8))
plt.show()