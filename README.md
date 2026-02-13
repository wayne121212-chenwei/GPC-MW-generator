# GPC 圖譜分子量計算程式

此專案提供一個命令列工具，可根據 GPC 資料計算：
- Mw
- Mn
- PDI

功能包含：
1. 讀取 GPC 數據（`time`, `intensity`）
2. 套用檢量線公式（例如 `logM=-0.45*t+12.3`）
3. 在指定積分範圍內做**兩點式基線修正**
4. 輸出 Mw / Mn / PDI

## 我要怎麼把數據輸入進去？

### 1) 先準備 CSV 檔
請建立資料檔（`.csv` 或 `.txt`）

支援兩種格式：
1. **有欄位名稱的 CSV**（至少有 `time`, `intensity`）
2. **無欄位名稱的兩欄數值格式**（每行 `time intensity`，可用空白或 tab 分隔）

至少要有兩個數值欄：
- `time`：保留時間（分鐘）
- `intensity`：訊號強度

例如（也可直接用專案內的 `sample_gpc_data.csv`）：

例如你貼的資料也可以直接讀取：

```text
0.0000   -0.1606
0.0017   -0.1606
0.0033   -0.1611
...
```


```csv
time,intensity
18.00,120
18.50,160
19.00,220
19.50,310
20.00,280
...
```

> 你的儀器資料如果欄名不是 `time` / `intensity`，可以用 `--time-col`、`--intensity-col` 指定。

### 2) 執行程式

```bash
python gpc_calculator.py \
  --data sample_gpc_data.csv \
  --formula="-0.45*t+12.3" \
  --range 19 31
```

參數說明：
- `--data`：你的 CSV 路徑
- `--formula`：檢量線公式（需輸出 `log10(M)`）
- `--range START END`：積分範圍（例如 `19 31`）

### 3) 看輸出
程式會輸出：
- `Mw`
- `Mn`
- `PDI`

例如：

```text
Mw: 1.23e+05
Mn: 8.90e+04
PDI: 1.38
```

## 使用方式（通用）

```bash
python gpc_calculator.py \
  --data your_data.csv \
  --formula="logM=-0.45*t+12.3" \
  --range 19 31
```

可選參數：
- `--time-col`：時間欄位名稱（預設 `time`）
- `--intensity-col`：強度欄位名稱（預設 `intensity`）

## 計算說明

- 在積分範圍起點與終點做內插，建立邊界點。
- 使用範圍兩端點強度建立線性基線，逐點扣除（負值截為 0）。
- 檢量線公式輸出 `log10(M)`，故 `M = 10^(logM)`。
- 以校正後強度作為權重估算：
  - `Mn = Σw / Σ(w/M)`
  - `Mw = Σ(w*M) / Σw`
  - `PDI = Mw / Mn`


## 可以直接在 PC 打開嗎？可以。

你有兩種方式：

### A) 命令列模式（原本方式）
```bash
python gpc_calculator.py --data your_data.csv --formula="-0.45*t+12.3" --range 19 31
```

### B) 桌面視窗模式（新）
```bash
python gpc_gui.py
```

開啟後可直接：
1. 點「選擇檔案」載入 CSV。
2. 輸入檢量線公式、積分範圍。
3. 按「開始計算」，視窗會顯示 Mw / Mn / PDI。

> 若你想讓同事在沒有 Python 的 PC 直接雙擊執行，可再用 PyInstaller 打包成 `.exe`。
