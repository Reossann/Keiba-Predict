import pandas as pd
from sklearn.preprocessing  import LabelEncoder
from sklearn.model_selection import train_test_split
import lightgbm as lgb
from sklearn.metrics import accuracy_score, roc_auc_score
import matplotlib.pyplot as plt
import japanize_matplotlib # 日本語表示のためのライブラリ
import joblib

# 1. 保存したデータベースを読み込む
# この一行で、これまでの苦労の成果を瞬時に呼び出せる
df = pd.read_csv('Race_database_2025_6.csv') 
encoders={}
# 2. エンコーディング処理を行う
# (ここに前回のヒントであるLabelEncoderのコードが入る)
categorical_cols = ['騎手', '馬名', '厩舎',"年齢","斤量","馬体重（増減）"]
for col in categorical_cols:
    le = LabelEncoder()
    df[col + "_enc"] = le.fit_transform(df[col])
    encoders[col] = le
joblib.dump(encoders, 'encoders.joblib')

# 3. この後のモデル学習なども、このdfを使って進めていく

# 1. 特徴量（X）と目的変数（y）を定義
feature_columns = ['騎手_enc', '馬名_enc', '厩舎_enc', "年齢_enc","斤量_enc","馬体重（増減）_enc"] # 予測に使いたい列を全て選ぶ
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