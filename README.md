# gen-gantt

YAML で定義したタスク構造を読み込み、日 / 週 / 月で折りたたみ可能なガントチャート Excel ファイルを生成する Python スクリプト。

## 特長

- **3 段階の列折りたたみ**: 日 / 週 / 月でアウトライン切り替え
- **3 段階の行折りたたみ**: フェーズ / タスク / サブタスクの階層表示
- **役割 / 担当者列**: 左端に役割・担当者を明示
- **階層別カラーバー**: 濃 / 中 / 薄の 3 色でフェーズ・タスク・サブタスクを区別
- **ウィンドウ枠固定**: ラベル列とヘッダ行を常に表示

## 必要環境

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) によるパッケージ管理
- 依存パッケージ: `openpyxl`, `PyYAML`（`uv sync` で自動インストール）

```bash
uv sync
```

> `uv` 未インストールの場合は次のいずれかでインストール:
>
> ```bash
> # macOS / Linux
> curl -LsSf https://astral.sh/uv/install.sh | sh
>
> # pip 経由
> pip install uv
> ```

## 使い方

### 基本

```bash
# カレントディレクトリに出力
uv run python generate_gantt.py examples/sample.yaml

# 出力先を指定
uv run python generate_gantt.py examples/sample.yaml --output ./out
```

出力ファイル名は `{project.name}_gantt.xlsx`。

### 引数

| 引数         | 必須 | デフォルト        | 説明              |
| ---------- | -- | ------------ | --------------- |
| `input`    | ✅  | -            | 入力 YAML ファイルパス  |
| `--output` | ❌  | カレントディレクトリ   | 出力先ディレクトリ       |

## YAML フォーマット

```yaml
project:
  name: "プロジェクト名"          # 出力ファイル名にも使われる
  start: "2025-06-01"           # ISO 8601
  end: "2025-08-31"             # ISO 8601
  week_start: "monday"          # "monday" または "sunday"

tasks:
  - id: "phase1"                # プロジェクト内でユニーク
    name: "フェーズ1"
    level: 0                    # 0=フェーズ / 1=タスク / 2=サブタスク
    role: "PM"                  # 任意
    assignee: "山田"             # 任意
    children:
      - id: "task1-1"
        name: "要件定義"
        level: 1
        role: "アナリスト"
        assignee: "佐藤"
        start: "2025-06-01"     # level >= 1 で必須
        end: "2025-06-14"       # level >= 1 で必須
        children:
          - id: "subtask1-1-1"
            name: "ヒアリング"
            level: 2
            start: "2025-06-01"
            end: "2025-06-07"
```

### フィールド一覧

#### `project`

| キー           | 型      | 必須 | 説明                              |
| ------------ | ------ | -- | ------------------------------- |
| `name`       | string | ✅  | プロジェクト名。出力ファイル名にも使われる            |
| `start`      | date   | ✅  | プロジェクト開始日（ISO 8601）             |
| `end`        | date   | ✅  | プロジェクト終了日（ISO 8601）             |
| `week_start` | string | ❌  | `"monday"`(既定) または `"sunday"`   |

#### `tasks[*]`

| キー         | 型       | 必須                    | 説明                                  |
| ---------- | ------- | --------------------- | ----------------------------------- |
| `id`       | string  | ✅                     | プロジェクト内でユニーク                        |
| `name`     | string  | ✅                     | タスク名                                |
| `level`    | int     | ✅                     | `0`=フェーズ / `1`=タスク / `2`=サブタスク      |
| `start`    | date    | level ≥ 1 で必須          | 開始日。level 0 では子から自動算出               |
| `end`      | date    | level ≥ 1 で必須          | 終了日（end-inclusive）                   |
| `role`     | string  | ❌                     | 役割                                  |
| `assignee` | string  | ❌                     | 担当者                                 |
| `children` | list    | level 0 で必須、それ以下では任意   | 子タスク。level は親 + 1 でなければならない          |

### ルール

- `level` は 0 / 1 / 2 の 3 階層のみ。親より 1 だけ深い `level` を持つこと
- level 0（フェーズ）は `start` / `end` の指定不要 — 子から自動算出
- level 1 以上は `start` / `end` が必須
- すべての日付は `project.start`〜`project.end` の範囲内に収める
- `id` はプロジェクト内でユニーク
- 日付バーは `start` / `end` ともに含む（end-inclusive）

## 生成された Excel の操作

### シートレイアウト

| 列           | 内容              |
| ----------- | --------------- |
| A           | 役割              |
| B           | 担当者             |
| C           | タスク名（階層分インデント） |
| D           | 開始日             |
| E           | 終了日             |
| F 以降        | 日付列（1 列 = 1 日）  |

| 行  | 内容                      |
| -- | ----------------------- |
| 1  | 月ラベル (`2025-06`)        |
| 2  | 週ラベル (`W23`)            |
| 3  | 日ラベル (`1`, `2`, ...)    |
| 4〜 | タスク行                    |

### 列の折りたたみ（日 / 週 / 月切替）

シート左上のアウトラインボタン `1 / 2 / 3` をクリック:

| ボタン | 表示                  |
| --- | ------------------- |
| 1   | 月の先頭日のみ（最も折りたたまれた状態） |
| 2   | + 週の先頭日             |
| 3   | すべての日を表示            |

月をまたぐ週は月の区切りで自動的に分割される。

### 行の折りたたみ（階層切替）

行側のアウトラインボタンも同様に 3 段階:

| ボタン | 表示              |
| --- | --------------- |
| 1   | フェーズ行のみ         |
| 2   | + タスク行          |
| 3   | + サブタスク行（全行表示）  |

### ウィンドウ枠固定

`F4` で固定済。左 5 列（役割・担当者・タスク名・開始日・終了日）と上 3 行（月・週・日ラベル）はスクロール中も常に表示される。

### 配色

| 階層    | バーの色    | 行のフォント |
| ----- | ------- | ------ |
| level 0 (フェーズ) | 濃いブルー   | 太字     |
| level 1 (タスク)  | ミディアムブルー | 標準     |
| level 2 (サブタスク) | ライトブルー  | グレー    |

## エラーハンドリング

以下に該当すると標準エラー出力にメッセージを出力し、exit code `1` で終了する:

- 入力 YAML が存在しない
- `project.start > project.end`
- level 1 以上のタスクで `start` / `end` が未定義
- タスクの日付が `project.start`〜`project.end` の範囲外
- `id` が重複している

例:

```bash
$ uv run python generate_gantt.py missing.yaml
error: Input YAML not found: missing.yaml
$ echo $?
1
```

## ファイル構成

```
generate_gantt.py        # CLI エントリポイント
gantt/
  __init__.py
  loader.py              # YAML 読み込みとバリデーション
  layout.py              # 日付列・タスク行レイアウト計算
  writer.py              # openpyxl による Excel 書き出し
examples/
  sample.yaml            # サンプル入力
pyproject.toml           # 依存定義（uv で管理）
uv.lock                  # 依存ロックファイル
```

## サンプル

`examples/sample.yaml` に 3 フェーズ・6 タスク・4 サブタスクのサンプルが含まれている:

```bash
uv run python generate_gantt.py examples/sample.yaml --output ./out
open "out/Sample Project_gantt.xlsx"
```

## 非対応事項

以下はスコープ外:

- タスク間の依存関係（矢印）
- マイルストーン
- 進捗率の表示
- Excel 以外のフォーマット出力
