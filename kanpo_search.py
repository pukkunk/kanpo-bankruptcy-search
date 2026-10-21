# -*- coding: utf-8 -*-
import argparse
import fnmatch
import os
import platform
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import List

try:
    import fitz  # PyMuPDF
except ImportError as e:
    msg = "The 'pymupdf' module is required but not installed.\n"
    msg += "You can install it with: pip install pymupdf\n"
    msg += f"Details: {e}"
    print(msg)
    raise SystemExit(1)

try:
    import ini_cfg_parser as ini
except ImportError as e:
    msg = "The 'ini_cfg_parser' module is required but not installed.\n"
    msg += "You can install it with: pip install ini_cfg_parser\n"
    msg += f"Details: {e}"
    print(msg)
    raise SystemExit(1)

OK_VAL = 0
NG_VAL = 1

__version_short__ = f"0.0.1, python={platform.python_version()} {platform.architecture()[0]}"
__version__ = f"{__version_short__}\n"
__copyright__ = "pukkunk"
__author__ = "pukkunk"

if getattr(sys, "frozen", False):
    # PyInstallerでEXE化した場合
    SCR_PATH = Path(sys.executable).resolve()
else:
    # Pythonスクリプトとして実行した場合
    SCR_PATH = Path(__file__).resolve()

DEFAULT_INI = SCR_PATH.with_suffix(".ini")

def get_ini_dict_val() -> ini.IniDict:
    """INIのデフォルト値と型を定義する。"""
    return {
        "官報": {
            "裁判所": {"type": str, "inf": "*地方裁判所*"},
            "段組数": {"type": int, "inf": 4},
            "公告": {"type": List[str], "inf": ["破産手続開始"]},
        },
        "OCR": {
            "実行ファイル": {"type": str, "inf": ""},
            "言語": {"type": str, "inf": "jpn"},
            "PSM": {"type": int, "inf": 6},
            "解像度": {"type": int, "inf": 300},
        },
        "出力": {
            "文字コード": {"type": str, "inf": "utf-8"},
        },
    }


def read_ini(ini_path: Path):
    """ini_cfg_parserで設定を読み込む。"""
    parser = ini.IniParser(str(ini_path), get_ini_dict_val(), "utf8")
    return parser


def create_default_ini(ini_path: Path) -> None:
    """INIが存在しない場合にデフォルト値でINIを作成する。"""
    ini_values = get_ini_dict_val()

    lines = []

    for section, values in ini_values.items():
        lines.append(f"[{section}]")

        for key, value in values.items():
            default_value = value["inf"]

            if isinstance(default_value, list):
                default_value = ",".join(str(x) for x in default_value)
            else:
                default_value = str(default_value)

            lines.append(f"{key}={default_value}")

        lines.append("")

    ini_path.parent.mkdir(parents=True, exist_ok=True)

    with open(ini_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))


def split_patterns(value):
    """カンマ区切りのワイルドカードをパターン一覧にする。"""
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return [str(x).strip() for x in value if str(x).strip()]


def wildcard_match(text, patterns):
    """* と ? を使って文字列を判定する。"""
    text = text.strip()
    return any(fnmatch.fnmatchcase(text, pattern) for pattern in patterns)


def find_tesseract(configured_path: str) -> str:
    """INI指定またはPATH/Windows標準的な場所からTesseractを探す。"""
    if configured_path:
        path = Path(os.path.expandvars(os.path.expanduser(configured_path)))
        if path.exists():
            return str(path)

    found = shutil.which("tesseract")
    if found:
        return found

    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)

    raise FileNotFoundError(
        "Tesseract OCR が見つかりません。INIの [OCR] 実行ファイル に "
        "tesseract.exe のフルパスを指定してください。"
    )


def run_tesseract(tesseract, image_path, language, psm):
    """Tesseractを実行してOCR文字列を取得する。"""
    command = [
        tesseract,
        str(image_path),
        "stdout",
        "-l",
        language,
        "--psm",
        str(psm),
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Tesseract OCRに失敗しました。\n{result.stderr.strip()}"
        )
    return result.stdout


def normalize_text(text):
    """OCR結果の最低限の正規化。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def extract_court(text):
    """OCR結果から裁判所名らしき行を取得する。"""
    for line in text.splitlines():
        line = line.strip()
        if "地方裁判所" in line or "家庭裁判所" in line:
            return line
    return ""


def contains_announcement(text, announcement_patterns):
    """指定された公告名のいずれかがOCR結果に含まれるか判定する。"""
    return any(pattern in text for pattern in announcement_patterns)


def process_pdf(pdf_path, ini_path, name):
    """PDFを4段組などの指定でOCRし、条件に一致する公告をTXTへ出力する。"""
    ini_parser = read_ini(ini_path)

    court_patterns = split_patterns(ini_parser.get("官報", "裁判所"))
    announcement_patterns = split_patterns(ini_parser.get("官報", "公告"))
    columns = ini_parser.get("官報", "段組数")
    tesseract_path = ini_parser.get("OCR", "実行ファイル")
    language = ini_parser.get("OCR", "言語")
    psm = ini_parser.get("OCR", "PSM")
    dpi = ini_parser.get("OCR", "解像度")
    output_encoding = ini_parser.get("出力", "文字コード")

    if columns < 1:
        raise ValueError("段組数は1以上を指定してください。")

    tesseract = find_tesseract(tesseract_path)

    output_path = pdf_path.with_suffix(".txt")
    matches = []

    print(f"入力PDF : {pdf_path}")
    print(f"INI     : {ini_path}")
    print(f"裁判所  : {', '.join(court_patterns)}")
    print(f"公告    : {', '.join(announcement_patterns)}")
    print(f"段組数  : {columns}")
    print(f"OCR     : {tesseract}")
    if name:
        print(f"氏名    : {name}")
    else:
        print("氏名    : 指定なし")

    with fitz.open(pdf_path) as document:
        for page_no, page in enumerate(document, start=1):
            matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
            pix = page.get_pixmap(matrix=matrix, alpha=False)

            page_width = pix.width
            column_width = page_width / columns

            for column_no in range(columns):
                left = int(column_width * column_no)
                right = int(column_width * (column_no + 1))

                clip = fitz.Rect(
                    column_no * page.rect.width / columns,
                    0,
                    (column_no + 1) * page.rect.width / columns,
                    page.rect.height,
                )
                column_pix = page.get_pixmap(
                    matrix=matrix,
                    clip=clip,
                    alpha=False,
                )

                image_path = pdf_path.parent / (
                    f".{pdf_path.stem}_p{page_no:04d}_c{column_no + 1}.png"
                )
                column_pix.save(str(image_path))

                try:
                    text = normalize_text(
                        run_tesseract(
                            tesseract,
                            image_path,
                            language,
                            psm,
                        )
                    )
                finally:
                    try:
                        image_path.unlink()
                    except OSError:
                        pass

                if not text:
                    continue

                if not contains_announcement(text, announcement_patterns):
                    continue

                court = extract_court(text)

                if court and not wildcard_match(court, court_patterns):
                    continue

                if not court:
                    if not any(
                        pattern.replace("*", "") in text
                        for pattern in court_patterns
                        if pattern.replace("*", "")
                    ):
                        continue

                if name and name not in text:
                    continue

                matches.append(
                    {
                        "page": page_no,
                        "column": column_no + 1,
                        "court": court,
                        "text": text,
                    }
                )

    with open(output_path, "w", encoding=output_encoding) as fp:
        fp.write("検索結果\n")
        fp.write(f"入力PDF: {pdf_path}\n")
        fp.write(f"裁判所: {', '.join(court_patterns)}\n")
        fp.write(f"氏名: {name if name else '指定なし'}\n")
        fp.write(f"該当件数: {len(matches)}\n")
        fp.write("=" * 80 + "\n\n")

        for index, item in enumerate(matches, start=1):
            fp.write(f"[{index}]\n")
            fp.write(f"ページ: {item['page']}\n")
            fp.write(f"段: {item['column']}\n")
            fp.write(f"裁判所: {item['court']}\n")
            fp.write("-" * 80 + "\n")
            fp.write(item["text"])
            fp.write("\n\n")

    print(f"出力TXT : {output_path}")
    print(f"該当件数: {len(matches)}")

    return OK_VAL


def main(args=None) -> None:
    parser = argparse.ArgumentParser(
        prog=SCR_PATH.name,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            f"""\
            version={__version__}
            官報の破産関連公告をOCRでテキスト化し、
            INIで指定した裁判所と、必要に応じて氏名で抽出します。

            Copyright :{__copyright__}
            author :{__author__}
            """
        ),
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{SCR_PATH.name} version={__version__}",
    )
    parser.add_argument(
        "input_pdf",
        help="入力する官報PDF",
    )
    parser.add_argument(
        "-n",
        "--name",
        help="氏名。指定した場合は裁判所 AND 氏名で絞り込みます。",
    )
    parser.add_argument(
        "-c",
        "--config",
        default=str(DEFAULT_INI),
        help=f"INIファイル。既定値: {DEFAULT_INI.name}",
    )

    parsed = parser.parse_args(args)

    pdf_path = Path(parsed.input_pdf).resolve()
    ini_path = Path(parsed.config).resolve()

    if not pdf_path.is_file():
        print(f"入力PDFが見つかりません: {pdf_path}")
        return NG_VAL

    if not ini_path.is_file():
        print(f"INIファイルがありません。デフォルト値で作成します: {ini_path}")
        try:
            create_default_ini(ini_path)
        except Exception as e:
            print(f"INIファイルの作成に失敗しました: {e}")
            return NG_VAL

        print(f"INIファイルを作成しました: {ini_path}")

    try:
        return process_pdf(pdf_path, ini_path, parsed.name)
    except Exception as e:
        print(f"ERROR: {e}")
        return NG_VAL


if __name__ == "__main__":
    sys.exit(main())
