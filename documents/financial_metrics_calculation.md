# 財務指標計算仕様

## 1. 目的

このドキュメントは、`FinancialMetricsCalculator`が計算する財務指標の定義と、欠損値などの取り扱いを説明する。

実装ファイル:

- `src/services/financial_metrics_calculator.py`

計算には、主に以下のSQLAlchemy ORMモデルを使用する。

- `FinancialStatement`: 財務情報
- `DailyPrice`: 日次株価

## 2. 共通仕様

### 2.1 戻り値の形式

自己資本比率、ROE、ROA、ROI、営業利益率、配当利回りは、百分率ではなく比率を`Decimal`で返す。

例:

```text
0.15 = 15%
0.075 = 7.5%
```

PERとPBRは比率ではなく倍率を返す。

```text
PER = 10  → 10倍
PBR = 1.5 → 1.5倍
```

### 2.2 欠損値と0除算

以下の場合、計算結果は`None`となる。

- 分子が`None`
- 分母が`None`
- 分母が`0`

0除算による例外は発生させない。

### 2.3 数値型

財務数値と計算結果には`Decimal`を使用する。これは、二進浮動小数点による意図しない丸め誤差を避けるためである。

## 3. 自己資本比率

### メソッド

```python
calculate_equity_ratio(statement)
```

### 計算式

```text
自己資本比率 = 自己資本 ÷ 総資産
```

### 使用する属性

| モデル | 属性 | 内容 |
|---|---|---|
| `FinancialStatement` | `equity` | 自己資本 |
| `FinancialStatement` | `total_assets` | 総資産 |

### 計算例

```text
自己資本 = 300
総資産   = 800

300 ÷ 800 = 0.375（37.5%）
```

## 4. ROE（自己資本利益率）

### メソッド

```python
calculate_roe(statement)
```

### 計算式

```text
ROE = 当期純利益 ÷ 自己資本
```

### 使用する属性

| モデル | 属性 | 内容 |
|---|---|---|
| `FinancialStatement` | `profit` | 当期純利益 |
| `FinancialStatement` | `equity` | 自己資本 |

### 計算例

```text
当期純利益 = 60
自己資本   = 300

60 ÷ 300 = 0.2（20%）
```

## 5. ROA（総資産利益率）

### メソッド

```python
calculate_roa(statement)
```

### 計算式

```text
ROA = 当期純利益 ÷ 総資産
```

### 使用する属性

| モデル | 属性 | 内容 |
|---|---|---|
| `FinancialStatement` | `profit` | 当期純利益 |
| `FinancialStatement` | `total_assets` | 総資産 |

### 計算例

```text
当期純利益 = 60
総資産     = 800

60 ÷ 800 = 0.075（7.5%）
```

## 6. ROI（投下資本利益率）

### メソッド

```python
calculate_roi(statement)
```

### 計算式

このアプリでは、投下資本を「自己資本＋負債」と定義する。

```text
投下資本 = 自己資本 + 負債
ROI      = 営業利益 ÷ 投下資本
```

したがって、実際の計算式は以下となる。

```text
ROI = 営業利益 ÷（自己資本 + 負債）
```

### 使用する属性

| モデル | 属性 | 内容 |
|---|---|---|
| `FinancialStatement` | `operating_profit` | 営業利益 |
| `FinancialStatement` | `equity` | 自己資本 |
| `FinancialStatement` | `liabilities` | 負債 |

### 計算例

```text
営業利益 = 100
自己資本 = 300
負債     = 500

100 ÷（300 + 500）= 0.125（12.5%）
```

### 注意事項

ROIには複数の定義が存在する。本アプリのROIは、有利子負債だけを使う定義ではなく、負債全体を投下資本に含める簡易的な定義である。

## 7. 営業利益率

### メソッド

```python
calculate_operating_margin(statement)
```

### 計算式

```text
営業利益率 = 営業利益 ÷ 売上高
```

### 使用する属性

| モデル | 属性 | 内容 |
|---|---|---|
| `FinancialStatement` | `operating_profit` | 営業利益 |
| `FinancialStatement` | `net_sales` | 売上高 |

### 計算例

```text
営業利益 = 100
売上高   = 1,000

100 ÷ 1,000 = 0.1（10%）
```

## 8. 株価関連指標

### メソッド

```python
calculate_price_metrics(statement, price)
```

このメソッドは、PER、PBR、配当利回りを辞書としてまとめて返す。

```python
{
    "per": Decimal("10"),
    "pbr": Decimal("2"),
    "dividend_yield": Decimal("0.025"),
}
```

### 8.1 使用する株価

株価は以下の優先順位で選択する。

1. `DailyPrice.adjusted_close`（調整後終値）
2. `DailyPrice.close`（終値）

調整後終値が`None`の場合だけ、通常の終値を使用する。両方とも`None`の場合、すべての株価関連指標は`None`となる。

### 8.2 PER（株価収益率）

```text
PER = 株価 ÷ EPS
```

| モデル | 属性 | 内容 |
|---|---|---|
| `DailyPrice` | `adjusted_close`または`close` | 株価 |
| `FinancialStatement` | `eps` | 1株当たり利益 |

計算例:

```text
株価 = 2,000円
EPS  = 200円

2,000 ÷ 200 = 10倍
```

### 8.3 PBR（株価純資産倍率）

```text
PBR = 株価 ÷ BPS
```

| モデル | 属性 | 内容 |
|---|---|---|
| `DailyPrice` | `adjusted_close`または`close` | 株価 |
| `FinancialStatement` | `bps` | 1株当たり純資産 |

計算例:

```text
株価 = 2,000円
BPS  = 1,000円

2,000 ÷ 1,000 = 2倍
```

### 8.4 配当利回り

```text
配当利回り = 1株当たり年間配当 ÷ 株価
```

| モデル | 属性 | 内容 |
|---|---|---|
| `FinancialStatement` | `dividend` | 1株当たり年間配当 |
| `DailyPrice` | `adjusted_close`または`close` | 株価 |

計算例:

```text
年間配当 = 50円
株価     = 2,000円

50 ÷ 2,000 = 0.025（2.5%）
```

## 9. 利用例

```python
from src.services.financial_metrics_calculator import (
    FinancialMetricsCalculator,
)

calculator = FinancialMetricsCalculator()

equity_ratio = calculator.calculate_equity_ratio(statement)
roe = calculator.calculate_roe(statement)
roa = calculator.calculate_roa(statement)
roi = calculator.calculate_roi(statement)
operating_margin = calculator.calculate_operating_margin(statement)
price_metrics = calculator.calculate_price_metrics(statement, price)
```

画面上で百分率として表示する場合は、計算結果を100倍して表示する。

```python
if roe is not None:
    display_value = f"{roe * 100:.2f}%"
```
