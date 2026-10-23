# -*- coding: utf-8 -*-
import argparse
import fnmatch
import os
import platform
import re
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

try:
    from PIL import Image
except ImportError as e:
    msg = "The 'Pillow' package is required but not installed.\n"  #修正
    msg += "You can install it with: python -m pip install Pillow\n"  #修正
    msg += f"Details: {e}"
    print(msg)
    raise SystemExit(1)

OK_VAL = 0
NG_VAL = 1

__version_short__ = f"0.0.2, python={platform.python_version()} {platform.architecture()[0]}"
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

# 情報元
# 官報情報サービス"掲載項目名一覧"
# https://search.npb.go.jp/OnlineHelp/pdf/KeisaiIndex.pdf?utm_source=chatgpt.com
ANNOUNCEMENT_HEADINGS = [
    '目次',
    '目次付録',
    '法令のあらまし',
    '憲法改正',
    '皇室典範',
    '詔書',
    '皇室令',
    '法律',
    '政令',
    '予算',
    '予算外国庫',
    '勅令',
    '閣令',
    '閣令・省令',
    '条約',
    '最高裁規則',
    '中央省庁等改革推進本部令',
    '内閣官房令',
    '内閣官房令・府令',
    '内閣官房令・府令・デジタル庁令',
    '内閣官房令・府令・デジタル庁令・復興庁令',
    '内閣官房令・府令・デジタル庁令・復興庁令・省令',
    '内閣官房令・府令・デジタル庁令・省令',
    '内閣官房令・府令・復興庁令',
    '内閣官房令・府令・復興庁令・省令',
    '内閣官房令・府令・省令',
    '内閣官房令・デジタル庁令',
    '内閣官房令・デジタル庁令・復興庁令',
    '内閣官房令・デジタル庁令・復興庁令・省令',
    '内閣官房令・デジタル庁令・省令',
    '内閣官房令・復興庁令',
    '内閣官房令・復興庁令・省令',
    '内閣官房令・省令',
    '府令',
    '府令・デジタル庁令',
    '府令・デジタル庁令・復興庁令',
    '府令・デジタル庁令・復興庁令・省令',
    '府令・デジタル庁令・省令',
    '府令・復興庁令',
    '府令・復興庁令・省令',
    '府令・省令',
    '府令・省令・本部令',
    'デジタル庁令',
    'デジタル庁令・復興庁令',
    'デジタル庁令・復興庁令・省令',
    'デジタル庁令・省令',
    '復興庁令',
    '復興庁令・省令',
    '省令・本部令',
    '省令・規則',
    '指令',
    '庁令・省令',
    '省令',
    '規則',
    '庁令',
    '訓令',
    '達',
    '告示',
    '告示・公示',
    '法規的告示',
    'その他告示',
    '予備費使用',
    '国会事項',
    '叙任及び辞令',
    '人事異動',
    '叙位・叙勲',
    '褒賞',
    '皇室事項',
    '法律施行通知',
    '官庁事項',
    '法務',
    '判決',
    '司法',
    '財政',
    '文教',
    '産業',
    '通運',
    '（労働）公労法に基づく争議行為の通知',
    '（労働）調停又は仲裁の申請及び紛争調停案の公表等',
    'その他の労働',
    '労働',
    '国家試験',
    '公聴会',
    '総理府公告',
    '内閣府公告',
    '郵政',
    'その他（官庁報告）',
    'その他（官庁報告・プライバシー）',
    'プライバシー等に配慮すべき告示',
    '閣議決定事項',
    '国際収支状況',
    '輸出信用状接受高',
    '国庫歳入歳出状況',
    '暦要項',
    'その他（資料）',
    '帝国議会',
    '地方自治事項',
    '公共企業体事項',
    '公庫事項',
    '日本弁護士連合会事項',
    'その他（官庁公告・会計検査院）',
    '日本学術会議会員選挙有権者名簿の縦覧',
    '特定非営利活動促進法第10条第2項の規定による公告',
    'その他（官庁公告・内閣府）',
    '職員の免職（懲戒）処分',
    'その他（官庁公告・公正取引委員会）',
    'その他（官庁公告・警察庁）',
    '入札公告',
    '無縁墳墓等改葬公告',
    '接収不動産関係',
    '日本国とアメリカ合衆国との間の相互協力及び安全保障条約六条関係告示',
    '住宅防音区域及び移転補償区域の指定等に関する公告',
    '指導公認会計士指定取消公告',
    '実務補習団体認定取消公告',
    '公認会計士懲戒処分公告',
    '外国証券会社に対する行政処分の公告',
    'その他（官庁公告・郵事庁）',
    '証券会社に対する行政処分の公告',
    'その他（官庁公告・金融庁）',
    'その他（官庁公告・総務省）',
    '押収物還付公告',
    '第三者所有物の没収関係',
    '工場財団',
    '鉱業財団',
    '漁業財団',
    '道路交通事業財団',
    '自動車交通事業財団',
    '港湾運送事業財団',
    '観光施設財団',
    '登記抹消公告',
    '商業登記抹消公告',
    '商号登記抹消公告',
    '有権者申出方',
    '営利職業紹介業者営業保証金取戻しに関する公告',
    '証券業者営業保証金取戻しに関する公告',
    '宅地建物取引業者営業保証金取戻しに関する公告',
    '割賦販売業者営業保証金取戻しに関する公告',
    '商品券発行業者営業保証金取戻しに関する公告',
    '家畜商営業保証金取戻しに関する公告',
    '供託金払渡し関係',
    '供託有価証券払渡請求に対する異議申出方公告',
    '公示送達',
    '職権抹消の公告',
    '司法書士懲戒処分公告',
    '土地家屋調査士懲戒処分公告',
    'その他（官庁公告・法務省）',
    'その他（官庁公告・外務省）',
    '特恵関税に関する特定特恵鉱工業産品等の輸入額等の公告',
    '実務補習団体認定',
    'ダイヤモンド売払公告',
    '投資顧問業者の営業保証金に係る仮配当表公示',
    '投資顧問業者の営業保証金に係る権利の実行に関する意見聴取会公示',
    '投資顧問業者の営業所の所在地の確知等に係る公告',
    '保険仲立人保証金取戻し公告',
    '証票無効（財務省）',
    '製造たばこ小売定価公告',
    '貸金業者に対する業務停止処分の公告',
    '外国為替及び外国貿易法第５５条の３第３項に規定する届出者に関する事項の公告',
    '投資顧問業者営業保証金取戻し公告',
    '投資顧問業者に対する行政処分の公告',
    '投資顧問業者の登録取消し処分の公告',
    '投資顧問業者の営業保証金に係る権利の実行',
    'その他（官庁公告・財務省）',
    '前払式証票発行者の発行保証金に係る債権の申出についての公示',
    '前払式証票発行者の発行保証金に係る仮配当表公示',
    '前払式証票発行者の発行保証金に係る配当表公示',
    '前払式証票発行者の発行保証金に係る権利実行に関する意見聴取会公示',
    '所在不明の貸金業者の公告',
    '半期報告書等の提出を要しない者を指定する公示',
    '前払式証票発行者の登録の取消し処分の公告',
    '貨幣セット販売価格公告',
    '税理士に対する懲戒処分公告',
    '物品税の販売業者証明書の無効公告',
    '証票無効（国税庁）',
    '公示送達（国税庁）',
    '納税証明書の無効公告',
    '税理士法第８条第１項第１０号に規定する研修の指定する公告',
    '税理士法第７条第２項及び第３項に規定する認定についての基準の公告',
    'その他（官庁公告・国税庁）',
    '著作権不明の著作物の使用に関する裁定',
    '観測ロケット実験実施',
    '法人設立許可取消処分公告',
    '審査事由説明書',
    'その他（官庁公告・文科省）',
    '証書無効（文化庁）',
    '出品預証書無効',
    '協同組合日本放送作家組合著作物使用料規程の一部変更要領',
    '社団法人日本文芸著作権保護同盟著作物使用規程の一部変更',
    'その他（官庁公告・文化庁）',
    'JIS表示許可工場（厚労省）',
    '法人の所在不明理事への申出の催告',
    '土木建築工事等の一般競争参加資格審査について',
    '証票無効（厚生労働省）',
    '公示送達（厚生労働省）',
    'その他（官庁公告・厚労省）',
    '現物給与の価格を定める公示',
    '保険医療機関若しくは保険薬局の指定又は特定承認保険医療機関の承認の取消し',
    '保険医又は保険薬剤師の登録の取消し',
    '国土調査法に基づく国土調査の成果の認証に準ずる指定の公告',
    '土地改良事業計画の公告',
    '土地改良事業計画の変更の公告',
    '土地改良事業の工事完了の公告',
    '土地改良区役員の退任及び就任の公告',
    '土地改良区連合役員の退任及び就任の公告',
    '土地改良区連合清算人の就任の公告',
    '土地改良区連合清算人の退任の公告',
    '土地改良区の定款変更認可の公告',
    '土地改良区連合の定款変更の公告',
    '土地改良区の解散に係る公告',
    '土地改良区の合弁認可公告',
    '土地改良区関係',
    '農用地整備事業の工事完了の公告',
    '農用地整備事業実施計画の変更の公告',
    '農用地整備事業の公告',
    '農用地保全事業の工事完了の公告',
    '農用地整備事業における換地処分の公告',
    '農用地整備事業における換地計画の公告',
    '農地法施行令関係',
    '農地の買収前の所有者等への売払通知に代える公告',
    '換地計画の公告',
    '解散命令',
    '建設事業の工事完了の公告',
    '直轄災害復旧事業の工事完了公告',
    '国土調査法施行令関係',
    '国有財産売払公告',
    'その他（官庁公告・農林水産省）',
    'その他（官庁公告・林野庁）',
    '割賦販売法施行令第七条第一項の規定に基づく公示',
    '割賦販売法に基づく同法第３５条の３の２の許可を受けた者の営業廃止に関する公示',
    '割賦販売法及び割賦販売法施行令に基づく債権の申出に関する公示',
    '割賦販売法施行令に基づく債権の申出に関する公示',
    '割賦販売法に基づく登録割賦購入あっせん業者の営業廃止に関する公示',
    '割賦販売法第４３条第１項の規定に基づく公告',
    '割賦販売法施行令第９条第１項の規定に基づく配当表の公告',
    '割賦販売法第二十六条の規定に係る公示',
    '行政手続法第１５条第３項の規定による公告',
    '前払式特定取引業者の営業保証金及び前受業務保証金の還付に係る権利の調査についての意見徴収会の開催公示',
    '許可割賦販売業者等の営業保証金等に関する規則第４条の規定に基づく仮配当表の公示',
    '新エネルギー・産業技術総合開発機構の販売するアルコールの価格の認可公告',
    'ＪＩＳ表示許可工場（経産省）',
    'その他（官庁公告・経産省）',
    '鉱業法第１４２条の規定による公告',
    '鉱業法第１８９条の規定による公告',
    'その他（官庁公告・資源エネルギー庁）',
    '公示送達（特許庁）',
    'その他（官庁公告・特許庁）',
    '建設業の営業の停止命令の公告',
    '建設業の許可の取消処分の公告',
    '不動産鑑定士に対する懲戒処分公告',
    '審理報告書提出の公示',
    'JIS表示許可工場（国交省）',
    '自動車の移転登録の登録抹消に関する公告',
    '自動車の登録の抹消に関する公告',
    '自動車の登録番号の無効に関する公告',
    '回送運転許可番号標の無効公告',
    '臨時運転許可番号標の無効公告',
    '宅地建物取引業法第６７条に基づく公告',
    '積立式宅地建物販売業法第２９条の規定に基づく公告',
    '積立式宅地建物販売業法第３１条第１項の規定に基づく公告',
    '鉄道財団成立',
    '鉄道財団（催告）',
    '鉄道財団拡張の公告',
    '鉄道財団用紙閉鎖の公告',
    '軌道財団（催告）',
    '軌道財団拡張の公告',
    '軌道財団設定の公告',
    '軌道財団用紙閉鎖の公告',
    '軌道財団関係',
    '基本測量関係事項公告',
    '宅地建物取引業大臣免許の取消処分',
    '公共測量成果',
    '共同研究公募課題',
    'その他（官庁公告・国交省）',
    '自動車の自動車検査証及び登録番号標の無効に関する公告',
    '証票無効（海上保安庁）',
    'その他（官庁公告・海上保安庁）',
    '海難審判庁公告',
    'その他（官庁公告・海難審判庁公告）',
    '環境省が実施するダイオキシン類の請負調査の受注資格審査について',
    'その他（官庁公告・郵政省）',
    '証票無効（労働省）',
    '公示送達（労働省）',
    'その他（官庁公告・建設省）',
    '経済企画庁',
    '証票無効',
    'ＪＩＳ表示許可工場',
    '土地収用',
    '公判期日召喚の公示送達',
    'その他（官庁公告・環境省）',
    '隊員の免職（懲戒）処分',
    'その他（官庁公告・防衛省）',
    'その他（官庁公告・防衛施設庁）',
    'その他（官庁公告・プライバシーA）',
    'その他（官庁公告・永続A)',
    'その他（官庁公告・永続B)',
    '意思表示の公示送達',
    'その他（官庁公告・最高裁判所）',
    'その他（公示送達関係）',
    '相続財産管理人の選任',
    'その他（相続関係１）',
    '相続財産清算人の選任及び相続権主張の催告',
    'その他（相続清算）',
    '相続権主張の催告',
    'その他（相続関係）',
    'その他（相続関係２）',
    '禁治産宣告',
    '禁治産宣告取消',
    '準禁治産宣告',
    '準禁治産宣告取消',
    'その他（禁治産関係）',
    '公示催告',
    '公示催告（旧体裁）',
    '公示催告中更正',
    'その他（公示催告関係）',
    '失踪に関する届出の催告',
    '失踪宣告',
    '失踪宣告取消',
    'その他（失踪関係）',
    '除権判決',
    '除権決定',
    '除権判決（旧体裁）',
    '除権決定（旧体裁）',
    '除権判決中更正',
    'その他（除権判決関係）',
    '破産手続による包括的禁止命令',
    'その他（破産手続包括的禁止命令関係）',
    '破産手続による保全管理命令',
    'その他（破産手続保全管理命令関係）',
    '破産宣告',
    '破産宣告及び破産廃止',
    '破産宣告・破産廃止及び免責申立てに関する破産者審尋期日',
    '破産手続開始',
    '破産手続開始及び免責許可申立てに関する意見申述期間',
    '破産手続開始及び破産手続廃止',
    '破産手続開始・破産手続廃止及び免責許可申立てに関する意見申述期間',
    '破産廃止',
    'その他（破産手続開始関係）',
    '破産手続廃止',
    '破産宣告並びに同時廃止',
    '破産取消',
    '破産手続廃止及び免責許可決定',
    '破産手続開始の取消決定確定',
    '破産廃止の申立て',
    '破産手続廃止の申立て',
    '破産手続廃止の取消決定確定',
    'その他（破産手続廃止関係）',
    '破産終結',
    '破産手続終結',
    '破産手続終結及び免責許可決定',
    'その他（破産手続終結関係）',
    '小破産宣告',
    '破産債権の届出期間及び一般調査期日',
    '破産債権の届出期間及び一般調査期間',
    '破産債権の特別調査期日',
    '破産債権の特別調査期間',
    'その他（破産債権調査関係）',
    '破産管財人選任',
    '破産管財人変更',
    '破産管財人氏名変更',
    'その他（破産管財人関係）',
    '破産管財人住所変更',
    '破産管財人事務所変更',
    'その他（破産関係１）',
    '債権者集会招集及び免責申立てに関する破産者審尋期日',
    '最後配当に関する除斥期間',
    '債権者集会招集',
    '債権者集会招集及び免責許可申立てに関する意見申述期間',
    'その他（債権者集会招集関係）',
    '債権者集会期日',
    '書面による計算報告',
    '書面による計算報告及び免責許可申立てに関する意見申述期間',
    'その他（書面計算関係）',
    '債権者集会の決議に代わる決定',
    '強制和議のための債権者集会期日',
    '債権調査の特別期日',
    '債権調査の一般期日',
    'その他（破産関係２）',
    '免責申立てに関する破産者審尋期日',
    '免責許可申立てに関する意見申述期間',
    '免責決定',
    '免責許可決定',
    'その他（免責許可関係）',
    '免責取消',
    'その他（免責取消関係）',
    '免責決定確定',
    '免責決定確定・破産廃止',
    '免責決定確定・破産終結',
    '免責許可',
    'その他（免責関係）',
    '復権申立',
    '復権申立て',
    'その他（復権申立て関係）',
    '復権決定',
    'その他（復権関係）',
    '復権許可',
    'その他（復権決定関係）',
    '和議認可',
    '和議開始',
    '免責決定及び免責決定確定',
    '和議廃止',
    '強制和議集会期日',
    '強制和議認可',
    'その他（和議関係）',
    '特別清算開始',
    '特別清算終結',
    '特別清算協定認可',
    'その他（特別清算関係）',
    '会社整理開始',
    '会社整理終結',
    'その他（会社整理関係）',
    '更生計画認可',
    '更生計画変更認可',
    '更生手続開始',
    '更生手続終結',
    '更生手続廃止',
    'その他（更生関係１）',
    '関係人集会招集',
    '関係人集会期日',
    '管財人選任',
    '管財人辞任',
    '管財人変更',
    '管財人の死亡',
    '保全管財人選任',
    '保全管財人による管理人処分取消',
    '保全管財人による管理命令',
    'その他（更生関係２）',
    '更生計画不認可',
    '更生手続開始等',
    '更生手続開始の取消決定確定',
    '更生手続廃止の取消決定確定',
    '更生手続における包括的禁止命令',
    '更生手続における包括的禁止命令変更',
    '更生手続における包括的禁止命令取消',
    '更生手続における保全管理命令',
    '更生手続における保全管理命令変更',
    '更生手続における保全管理命令取消',
    '更生手続における監督命令',
    '更生手続における監督命令変更',
    '更生手続における監督命令取消',
    '更生会社の機関の権限回復',
    '更生会社の機関の権限回復の取消',
    '更生債権等の一般調査期間変更',
    '更生債権等の特別調査期間',
    '関係人集会期日等',
    'その他（企業担保関係）',
    'その他（船舶関係）',
    'その他（油濁損害関係）',
    '包括的禁止命令',
    '包括的禁止命令変更',
    '包括的禁止命令取消',
    '保全管理命令及び包括的禁止命令',
    '保全管理命令',
    '保全管理命令取消',
    '監督命令',
    '監督命令変更',
    '監督命令取消',
    '再生手続開始',
    '再生手続開始及び管理命令',
    '再生手続開始及び債権者集会招集',
    '再生手続開始の取消決定確定',
    '管理命令',
    '管理命令変更',
    '管理命令取消',
    '簡易再生',
    '同意再生',
    '営業譲渡に関する株主総会の決議に代わる許可',
    '資本の減少等を定めた再生計画案の提出の許可',
    '再生債権の特別調査期間',
    '再生債権の一般調査期間変更',
    '再生手続による債権者集会招集',
    '書面による決議に付する決定',
    'その他（再生関係１）',
    '監督委員事務所変更',
    '監督委員の解任及び選任',
    '監督委員の辞任及び選任',
    '監督委員変更',
    '再生手続開始及び監督命令',
    '再生債務者の株式の取得等を定めた再生計画案の提出の許可',
    '再生債務者の株式の取得等及び資本金の額の減少等並びに募集株式を引き受ける者の募集を定めた再生計画案の提出の許可',
    '再生債務者の資本金の額の減少等を定めた再生計画案の提出の許可',
    '新株発行を定めた再生計画案の提出の許可',
    '資本の減少等を定めた再生計画変更計画案の提出の許可',
    '事業譲渡に関する株主総会の決議による承認に代わる許可',
    '募集株式を引き受ける者の募集を定めた再生計画案の提出の許可',
    '募集株式を引き受ける者の募集を定めた再生計画案の提出の許可取消',
    '再生計画案の一般調査期間',
    '決議に付する決定',
    '再生計画の変更計画案を書面による決議に付する決定',
    '決議に付する決定の取消決定',
    '決議に付する決定及び債権者集会招集',
    '議決権行使の方法に関する定めの取消し及び債権者集会招集',
    '再生計画認可',
    '再生計画不認可',
    '再生手続終結',
    '再生手続廃止のための意見聴取期日招集',
    '再生手続廃止のための書面による意見聴取',
    '再生手続廃止',
    '再生手続廃止の取消決定確定',
    '再生計画取消',
    'その他（再生関係２）',
    '監督命令変更及び再生計画認可',
    '再生計画変更',
    '再生計画変更決定',
    '変更再生計画認可',
    '再生計画変更計画認可',
    '再生計画変更認可',
    '再生手続廃止及び包括的禁止命令',
    '再生手続廃止及び保全管理命令',
    '再生手続廃止及び保全管理命令の取消決定',
    '再生手続廃止・保全管理命令及び包括的禁止命令',
    '再生手続廃止及び監督命令変更',
    '再生手続廃止及び監督命令取消',
    '再生手続棄却',
    '小規模個人再生による再生手続開始',
    '小規模個人再生による再生手続開始の取消決定確定',
    '小規模個人再生による再生債権の届出期間変更',
    '小規模個人再生による再生債権の一般異議申述期間変更',
    '小規模個人再生による再生債権の特別異議申述期間',
    '小規模個人再生による書面決議に付する決定',
    'その他（小規模再生関係１）',
    '小規模個人再生による再生計画認可',
    '小規模個人再生による再生計画不認可',
    '小規模個人再生による再生計画取消',
    '小規模個人再生による再生手続廃止',
    '小規模個人再生による再生手続廃止の取消決定確定',
    '小規模個人再生による免責決定',
    'その他（小規模再生関係２）',
    '給与所得者等再生による再生手続開始',
    '給与所得者等再生による再生手続開始の取消決定確定',
    '給与所得者等再生による再生債権の届出期間変更',
    '給与所得者等再生による再生債権の一般異議申述期間変更',
    '給与所得者等再生による再生債権の特別異議申述期間',
    '給与所得者等再生による再生計画案についての意見聴取',
    'その他（給与再生関係１）',
    '給与所得者等再生による再生計画認可',
    '給与所得者等再生による再生計画不認可',
    '給与所得者等再生による再生計画取消',
    '給与所得者等再生による再生手続廃止',
    '給与所得者等再生による再生手続廃止の取消決定確定',
    '給与所得者等再生による免責決定',
    'その他（給与再生関係２）',
    '外国倒産処理手続の承認',
    '外国倒産処理手続の承認決定の取消決定確定',
    '強制執行等禁止命令',
    '承認援助手続による管理命令',
    '承認援助手続による保全管理命令',
    '外国倒産処理手続の承認及び強制執行等禁止命令',
    '外国倒産処理手続の承認及び管理命令',
    '外国倒産処理手続の承認・強制執行等禁止命令及び管理命令',
    '外国倒産処理手続の承認の取消し',
    '外国倒産処理手続の承認の取消しの取消決定確定',
    'その他（外国倒産関係）',
    '特殊法人等',
    '簡易確定手続開始（当事者及び共通義務が単数の場合）',
    '簡易確定手続開始（共通義務が複数の場合）',
    '簡易確定手続開始（和解金債権が存する旨を認める和解をした場合）',
    '対象債権の届出期間及び届出債権の認否期間の伸長',
    '届出債権の認否期間の伸長',
    '簡易確定手続申立団体の住所及び名称の変更',
    '簡易確定手続申立団体の名称の変更',
    '簡易確定手続申立団体の住所の変更',
    'その他（簡易確定関係）',
    '共有物の変更に係る裁判に関する異議の催告',
    '共有物の管理に係る裁判に関する異議の催告',
    '所在等不明共有者の持分の取得の裁判に関する異議の催告',
    '所在等不明共有者の持分を譲渡する権限の付与の裁判に関する異議の催告',
    '所有者不明土地及び建物管理命令に関する異議の催告',
    '所有者不明土地管理命令に関する異議の催告',
    '所有者不明建物管理命令に関する異議の催告',
    'その他',
    '共済組合',
    'その他（共済組合）',
    '独立行政法人理事就任関係',
    '独立行政法人財務諸表',
    'その他（独立行政法人）',
    '国立大学財務諸表',
    '大学共同利用機関法人財務諸表',
    'その他（国立大学・大学共同利用機関法人）',
    'その他特殊法人',
    '裁決の公告',
    '高速道路工事開始公告',
    '都道府県公債抽せん公告',
    '都道府県公債償還公告',
    '市公債抽せん公告',
    '市公債償還公告',
    '東京都区交付公債抽せん公告',
    '東京都区交付公債償還公告',
    '違法駐車車両保管公示（警察）',
    '違法駐車車両保管公示（交通安全協会）',
    '違法駐車車両保管公示',
    '所在不明の古物商・古物市場主の公告',
    '古物営業の許可の取消処分の公告',
    '積載物保管公示',
    '違法放置物件保管公示',
    '職員の免職処分',
    '教育職員免許状失効公告',
    '教育職員免許状取上げ処分公告',
    '各種公社',
    '行旅死亡人',
    '拾得物',
    '換地計画の縦覧',
    'その他（地方公共団体公告・永続）',
    '旅行業者営業保証金の権利実行申立てに係る公告',
    '旅行業者営業保証金の権利調査のための意見聴取会及び仮配当表に係る公告',
    '旅行業者営業保証金の権利実行のための配当表に係る公告',
    '旅行業者営業保証金の配当実施に係る公告',
    'その他（地方公共団体公告・プライバシー）',
    'その他（地方公共団体公告）',
    '合併公告１',
    '合併公告２',
    '合併公告',
    '合併並びに資本減少公告１',
    '合併並びに資本減少公告２',
    '合併並びに資本減少公告',
    '合併に伴なう資本減少公告',
    '合併につき株券等提出公告',
    '新設分割に伴う異議申述の公告',
    '吸収分割に伴う異議申述の公告',
    '会社分割につき株券提出公告',
    '吸収分割公告',
    '新設分割公告',
    '営業譲受公告',
    '資本の減少等及び新株発行を定めた再生計画案の提出の許可',
    '資本の減少等及び募集株式の発行を定めた再生計画案の提出の許可',
    '資本減少公告',
    '資本減少につき株券提出公告',
    '資本準備金をもってする株式の消却公告',
    '資本金及び準備金の額の減少公告',
    '利益準備金減少公告',
    '資本準備金及び利益準備金減少公告',
    '共同新設分割公告',
    '組織変更公告',
    '組織変更並びに資本減少公告',
    '効力発生日変更公告',
    '株式併合につき株券提出公告',
    '株式分割につき株券提出公告',
    '株式分割による株式割当日公告',
    '定款変更につき株券提出公告',
    '株式交換につき株券提出公告',
    '株式移転につき株券提出公告',
    '株式交換公告',
    '新株券発行につき株券提出公告',
    '（合併・資本減少）無効の提訴の公告',
    '解散公告（合名、合資会社）',
    '解散公告（１回のみ）',
    '解散公告（１）',
    '解散公告（２）',
    '解散公告（３）',
    '清算公告',
    '破産宣告申立の公告',
    '資本金の額の減少公告',
    '準備金の額の減少公告',
    '配当公告',
    '相続債権者受遺者への請求申出の催告',
    '所有者不明土地管理命令供託公告',
    '所有者不明建物管理命令供託公告',
    '所有者不明土地及び建物管理命令供託公告',
    '管理不全土地管理命令供託公告',
    '管理不全建物管理命令供託公告',
    '管理不全土地及び建物管理命令供託公告',
    '不在者財産の管理命令供託公告',
    '相続財産管理人による供託公告',
    'その他供託公告',
    '限定承認公告',
    '（営業・船舶）譲渡に関する異議申述公告',
    '貸付金の借入れに関する公告（電力会社）',
    '協定の変更等に関する公告（酒造組合）',
    '日本における代表者変更公告',
    '株券提出不能に対する異議申述公告',
    '所在不明株主の株式の競売又は売却に伴う異議申述の公告',
    '基準日設定につき通知公告',
    '新株式発行に関する取締役会決議公告',
    '第三者割当による新株式発行に関する取締役会決',
    '一単元の株式数の変更に関する取締役会決議公告',
    '自己株式の処分に関する取締役会決議公告',
    '新株予約権発行に関する取締役会決議公告',
    '新株式発行公告',
    '新株式割当日公告１',
    '新株式割当日公告２',
    '新株式割当日公告',
    '株式名義書換停止公告',
    '定款変更につき通知公告',
    '株式併合につき通知公告',
    '株式分割につき通知公告',
    '株式等無償割当てにつき通知公告',
    '株主割当ての株式等募集につき通知公告',
    '株式募集事項につき通知公告',
    '株式交付につき通知公告',
    '株式交換につき通知公告',
    '株式移転につき通知公告',
    '事業譲受けにつき通知公告',
    '株式譲渡制限設定につき株券提出公告',
    '全部取得条項付種類株式取得につき株券提出公告',
    '取得条項付株式取得につき株券提出公告',
    '組織変更につき株券等提出公告',
    '株式交換につき株券等提出公告',
    '株式移転につき株券等提出公告',
    '株式等売渡請求につき株券等提出公告',
    '株主総会決議（取消・無効）の訴提起の公告',
    '新株券交付請求に関する公告',
    '（農林・商工）債権売出公告',
    '社債募集公告',
    '社債総額減額契約締結公告',
    '担保変更・追加・追加変更公告',
    '取締役会決議公告関係',
    '社債権者集会召集公告関係',
    '外国会社の全ての日本における代表者の退任公告',
    '合併・資本減少等に係る訴提起の公告関係',
    '社債償還公告',
    '転換価格調整公告',
    '商標権の一部移転公告',
    '防災業務計画の修正要旨の公表について',
    '受託業務保証金取戻し公告',
    '商工組合中央金庫公告',
    '防災業務',
    '受託業務保証金取戻し公告関係',
    '家畜商営業保証金取戻し公告',
    '割賦販売業者営業保証金取戻し公告',
    '内航運送取扱業者営業保証金取戻し公告',
    '旅行業者営業保証金取戻し公告',
    '旅行業者営業保証金取戻し公告（共同）',
    '旅行業協会弁済業務保証金取戻し公告',
    '割賦販売業者営業保証金取戻し公告関係',
    '前払式特定取引業者営業保証金取戻し公告関係',
    '信託受益権販売業者営業保証金取戻し公告',
    '旅行業者営業保証金取戻し公告（単独）',
    '旅行業者営業保証金取戻し公告（共用）',
    '旅行業協会弁済業務保証金取戻し公告（共用）',
    '旅行業その他公告',
    '有料職業紹介事業保証金取戻し公告',
    '有料職業紹介事業保証金取戻し公告（単独）',
    '宅地建物取引業者営業保証金取戻し公告（単独）',
    '宅地建物取引業者営業保証金取戻し公告（共用）',
    '宅地建物取引業保証協会弁済業務保証金取戻し公告（不動産保証協会）',
    '宅地建物取引業保証協会弁済業務保証金取戻し公告（全国宅地建物取引業保証協会）',
    'その他公告（その他）',
    '宅地建物取引業者営業保証金取戻し公告',
    '宅地建物取引業保証協会弁済業務保証金取戻し公告',
    '宅地建物取引業（全国宅地建物取引業保証協会）',
    '決算公告（行）',
    'その他の枠付公告',
    '枠付公告（公）',
    '枠付公告（決算とその他の併せ）',
    '法人枠付公告（決算とその他の併せ）',
    '枠付広告（広）',
    '公益法人決算公告',
    '訂正公告',
    '訂正公告（会社用）',
    '訂正公告（扱店用）',
    '訂正公告（特殊法人用）',
    '訂正公告（特殊法人扱店用）',
    '取消公告',
    '取消公告（会社用）',
    '取消公告（特殊法人用）',
    '広告',
    '決算公告（枠）',
    '決算公告（法人枠）',
    'その他（会社等公・広告）',
    'その他公告（金融商品取引法）',
    'その他公告（法人法）',
    '正誤１',
    '正誤２（会社用）',
    '正誤',
    '記事正誤',
    'お知らせ',
    'その他の記事',
    'その他の宣伝',
    '資料版記事',
    '目録記事',
    '入札公告〔物品等・サービス一般〕',
    '入札公告〔物品等・サービス一般〕の変更',
    '入札公告〔物品等・サービス一般〕の訂正',
    '入札公告〔物品等・サービス一般〕の取消',
    '入札公告（建設工事）',
    '入札公告（建設工事）の変更',
    '入札公告（建設工事）の訂正',
    '入札公告（建設工事）の取消',
    '入札公告の変更・訂正・取消',
    'その他（入札公告）',
    '入札公示〔物品等・サービス一般〕',
    '入札公示〔物品等・サービス一般〕の変更',
    '入札公示〔物品等・サービス一般〕の訂正',
    '入札公示〔物品等・サービス一般〕の取消',
    '入札公示（建設工事）',
    '入札公示（建設工事）の変更',
    '入札公示（建設工事）の訂正',
    '入札公示（建設工事）の取消',
    '入札公示（建築のためのサービスその他技術的サービス（建設工事を除く））',
    '入札公示（建築のためのサービスその他技術的サービス（建設工事を除く））の変更',
    '入札公示（建築のためのサービスその他技術的サービス（建設工事を除く））の訂正',
    '入札公示（建築のためのサービスその他技術的サービス（建設工事を除く））の取消',
    '公募型競争入札方式に係る手続開始の公示（建築のためのサービスその他技術的サービス（建設工事を除く））',
    '公募型競争入札方式に係る手続開始の公示（建築のためのサービスその他技術的サービス（建設工事を除く））の変更',
    '公募型競争入札方式に係る手続開始の公示（建築のためのサービスその他技術的サービス（建設工事を除く））の訂正',
    '公募型競争入札方式に係る手続開始の公示（建築のためのサービスその他技術的サービス（建設工事を除く））の取消',
    '公募型競争入札方式に係る手続開始の公示',
    '公募型競争入札方式に係る手続開始の公示の変更',
    '公募型競争入札方式に係る手続開始の公示の訂正',
    '公募型競争入札方式に係る手続開始の公示の取消',
    '公募型プロポーザル方式に係る手続開始の公示（建築のためのサービスその他技術的サービス（建設工事を除く））',
    '公募型プロポーザル方式に係る手続開始の公示（建築のためのサービスその他技術的サービス（建設工事を除く））の変更',
    '公募型プロポーザル方式に係る手続開始の公示（建築のためのサービスその他技術的サービス（建設工事を除く））の訂正',
    '公募型プロポーザル方式に係る手続開始の公示（建築のためのサービスその他技術的サービス（建設工事を除く））の取消',
    '公募型プロポーザル方式に係る手続開始の公示',
    '公募型プロポーザル方式に係る手続開始の公示の変更・訂正・取消',
    '公募型プロポーザル方式に係る手続開始の公示の変更',
    '公募型プロポーザル方式に係る手続開始の公示の訂正',
    '公募型プロポーザル方式に係る手続開始の公示の取消',
    '入札公示',
    '入札公示の変更・訂正・取消',
    'その他（入札公示）',
    '競争参加者の資格に関する公示',
    '競争参加者の資格に関する公示の変更',
    '競争参加者の資格に関する公示の訂正',
    '競争参加者の資格に関する公示の取消',
    '閲覧窓口等',
    '閲覧窓口等の変更',
    '閲覧窓口等の訂正',
    '閲覧窓口等の取消',
    'その他（資格）',
    '入札公告（公示）予定の公示（共同）',
    '入札公告（公示）予定の公示（単独）',
    '入札公告（公示）予定の公示',
    '入札公告（公示）予定の公示の変更',
    '入札公告（公示）予定の公示の訂正',
    '入札公告（公示）予定の公示の取消',
    'コンピューター製品及びサービスの調達予定の公示（共同）',
    'コンピューター製品及びサービスの調達予定の公示（単独）',
    'コンピュータ及びサービスの調達予定の公示',
    'コンピューター製品及びサービスの調達予定の公示の変更',
    'コンピューター製品及びサービスの調達予定の公示の訂正',
    'コンピューター製品及びサービスの調達予定の公示の取消',
    '電気通信機器及びサービスの調達予定の公示（共同）',
    '電気通信機器及びサービスの調達予定の公示（単独）',
    '電気通信機器及びサービスの調達予定の公示',
    '電気通信機器及びサービスの調達予定の公示の変更',
    '電気通信機器及びサービスの調達予定の公示の訂正',
    '電気通信機器及びサービスの調達予定の公示の取消',
    '医療技術製品及びサービスの調達予定の公示（共同）',
    '医療技術製品及びサービスの調達予定の公示（単独）',
    '医療技術製品及びサービスの調達予定の公示',
    '医療技術製品及びサービスの調達予定の公示の変更',
    '医療技術製品及びサービスの調達予定の公示の訂正',
    '医療技術製品及びサービスの調達予定の公示の取消',
    '入札公告予定の公示',
    '入札公告予定の公示の変更・訂正・取消',
    'その他（調達予定）',
    '資料提供招請に関する公表',
    '資料提供招請に関する公表の変更',
    '資料提供招請に関する公表の訂正',
    '資料提供招請に関する公表の取消',
    '意見招請に関する公示',
    '意見招請に関する公示の変更',
    '意見招請に関する公示の訂正',
    '意見招請に関する公示の取消',
    '提案要請に関する公示',
    '提案要請に関する公示の変更',
    '提案要請に関する公示の訂正',
    '提案要請に関する公示の取消',
    '参加招請に関する公示',
    '参加招請に関する公示の変更',
    '参加招請に関する公示の訂正',
    '参加招請に関する公示の取消',
    '設計等提案書提出に関する公示',
    '設計等提案書提出に関する公示の変更',
    '設計等提案書提出に関する公示の訂正',
    '設計等提案書提出に関する公示の取消',
    'その他（招請）',
    '随意契約に関する公示',
    '随意契約に関する公示の変更',
    '随意契約に関する公示の訂正',
    '随意契約に関する公示の取消',
    'その他（随意契約）',
    '落札者等の公示（共同）',
    '落札者等の公示（単独）',
    '落札者等の公示',
    '落札者等の公示の変更',
    '落札者等の公示の訂正',
    '落札者等の公示の取消',
    'その他（落札）',
    '報告（公表、統計の公表等）',
    '報告（公表、統計の公表等）の変更',
    '報告（公表、統計の公表等）の訂正',
    '報告（公表、統計の公表等）の取消',
    '調達機関の窓口リスト',
    '調達機関の窓口リストの変更',
    '調達機関の窓口リストの訂正',
    '調達機関の窓口リストの取消',
    'その他（報告）',
    'その他（政府調達）',
]


def get_ini_dict_val():
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
            "中間データ出力": {"type": int, "inf": 0},
        },
        "出力": {
            "文字コード": {"type": str, "inf": "utf-8"},
        },
    }


def create_default_ini(ini_path: Path) -> None:
    """INIファイルが存在しない場合、デフォルト設定で作成する。"""
    ini_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "; 官報検索設定",
        "; 日本語UTF-8で保存してください。",
        "",
        "[官報]",
        "; 裁判所はワイルドカード * と ? に対応",
        "; 複数指定する場合はカンマ区切り",
        "裁判所=*地方裁判所*",
        "",
        "; 今回の官報は4段組",
        "段組数=4",
        "",
        "; OCRで抽出対象にする公告名",
        "; 複数指定する場合はカンマ区切り",
        "公告=破産手続開始,破産手続開始及び免責許可申立てに関する意見申述期間",
        "",
        "[OCR]",
        "; 空欄ならPATHまたは標準的なWindowsインストール先を検索",
        "実行ファイル=",
        "言語=jpn",
        "PSM=6",
        "解像度=300",
        "中間データ出力=0",
        "",
        "[出力]",
        "文字コード=utf-8",
        "",
    ]
    ini_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"INIファイルを作成しました: {ini_path}")


def read_ini(ini_path: Path):
    return ini.IniParser(str(ini_path), get_ini_dict_val(), "utf8")


def split_patterns(value):
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return [str(x).strip() for x in value if str(x).strip()]


def wildcard_match(text, patterns):
    text = text.strip()
    return any(fnmatch.fnmatchcase(text, pattern) for pattern in patterns)


def find_tesseract(configured_path: str) -> str:
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
    command = [
        tesseract, str(image_path), "stdout",
        "-l", language, "--psm", str(psm),
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
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def normalize_heading(text):
    """見出し比較用。OCRによる改行・空白の差を吸収する。"""
    return re.sub(r"\s+", "", text).strip()


def heading_line_matches(compact, normalized_heading):
    """OCRで見出し末尾に混入する段番号・罫線由来文字などを許容して判定する。"""
    if compact == normalized_heading:
        return True
    if not compact.startswith(normalized_heading):
        return False

    # 官報OCRでは「破産手続開始 1 i」のように、見出しの後ろへ
    # 段番号や罫線由来の短い文字が混入することがある。
    suffix = compact[len(normalized_heading):]
    if len(suffix) > 4:
        return False
    return bool(re.fullmatch(r"[0-9０-９|｜:：iIlTt!]+", suffix))


def find_announcement_starts(stream):
    """官報掲載項目一覧から、公告見出しの開始位置を検出する。"""
    lines = stream.splitlines(keepends=True)
    starts = []
    offset = 0
    normalized_headings = sorted(
        ((normalize_heading(h), h) for h in ANNOUNCEMENT_HEADINGS),
        key=lambda x: len(x[0]),
        reverse=True,
    )

    for line_index, line in enumerate(lines):
        line_text = line.strip()
        if not line_text:
            offset += len(line)
            continue

        compact = normalize_heading(line_text)

        # 1行で見出しになっている場合。
        for normalized, heading in normalized_headings:
            if heading_line_matches(compact, normalized):
                starts.append((offset, heading))
                break
        else:
            # OCRで長い見出しが複数行に分割された場合。
            joined = compact
            for next_index in range(line_index + 1, min(line_index + 4, len(lines))):
                next_line = lines[next_index].strip()
                if not next_line:
                    continue
                joined += normalize_heading(next_line)
                found = False
                for normalized, heading in normalized_headings:
                    if heading_line_matches(joined, normalized):
                        starts.append((offset, heading))
                        found = True
                        break
                if found:
                    break
                if len(joined) > len(normalized_headings[0][0]):
                    break

        offset += len(line)

    # 同一位置の重複を除去。
    unique = []
    seen = set()
    for position, heading in sorted(starts, key=lambda x: (x[0], -len(x[1]))):
        key = (position, heading)
        if key not in seen:
            seen.add(key)
            unique.append((position, heading))
    return unique


def split_announcements(stream):
    """掲載項目見出しを境界として公告単位に分割する。"""
    starts = find_announcement_starts(stream)
    records = []
    for index, (start, heading) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(stream)
        body = stream[start:end].strip()
        if body:
            records.append((heading, body, start, end))
    return records

def announcement_matches_target(heading, target_patterns):
    """INIの[官報]公告で指定された掲載項目だけを抽出対象にする。"""
    # ANNOUNCEMENT_HEADINGSは公告の境界判定専用。抽出対象はINIだけで決める。
    normalized_heading = normalize_heading(heading)
    normalized_targets = {
        normalize_heading(x) for x in target_patterns if normalize_heading(x)
    }
    return normalized_heading in normalized_targets

def extract_court(text):
    for line in text.splitlines():
        line = line.strip()
        if "地方裁判所" in line or "家庭裁判所" in line:
            return line
    return ""


def court_matches(text, court_patterns):
    """公告本文の各行を調べ、指定した裁判所パターンに一致する行を探す。"""
    # OCRでは裁判所名の一部が誤認識されることがあるため、
    # 最初に見つかった「地方裁判所」だけで判定しない。各行を順番に調べる。
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "地方裁判所" not in line and "家庭裁判所" not in line:
            continue
        if wildcard_match(line, court_patterns):
            return True, line

    # OCRで「裁判所」の一部が欠落した場合などの保険。
    compact_text = normalize_heading(text)
    for pattern in court_patterns:
        literal = pattern.replace("*", "").replace("?", "")
        if literal and literal in compact_text:
            return True, ""
    return False, ""


def detect_body_horizontal_bounds(image, columns):
    """ページ上下に連続する縦罫線を検出し、本文領域の左右端を返す。"""
    gray = image.convert("L")
    width, height = gray.size

    # 黒画素の総数ではなく、各x列で上下方向に連続する黒画素の最長区間を調べる。
    # 左右の本文境界線は途中で途切れないという前提で、ページ高の75%以上の連続線を候補にする。
    threshold = 100
    min_run = int(height * 0.75)
    pixels = gray.load()
    candidate_x = []
    for x in range(width):
        longest_run = 0
        current_run = 0
        for y in range(height):
            if pixels[x, y] < threshold:
                current_run += 1
                if current_run > longest_run:
                    longest_run = current_run
            else:
                current_run = 0
        if longest_run >= min_run:
            candidate_x.append(x)

    # 太い縦罫線で隣接列が複数候補になる場合は、ひとつの線としてまとめる。
    groups = []
    for x in candidate_x:
        if not groups or x > groups[-1][-1] + 2:
            groups.append([x])
        else:
            groups[-1].append(x)
    line_positions = [round(sum(group) / len(group)) for group in groups]

    # ページ端の枠線などを避け、本文幅として十分離れた最外側の線を左右端にする。
    if len(line_positions) < 2:
        raise ValueError(
            f"本文左右端の連続縦罫線を検出できません。"
            f"最長連続線の閾値={min_run}px、検出候補={line_positions}"
        )
    left = line_positions[0]
    right = line_positions[-1]
    if right - left < width * 0.4:
        raise ValueError("検出した本文領域がページ幅に対して狭すぎます。")
    print(
        f"  本文境界検出: 左={left}, 右={right}, "
        f"上下連続縦罫線候補={line_positions}, 最小連続長={min_run}px, 段数={columns}"
    )
    return left, right


def process_pdf(pdf_path, ini_path, name):
    """PDFをOCRし、次の段・次のページに続く公告を結合して抽出する。"""
    ini_parser = read_ini(ini_path)

    court_patterns = split_patterns(ini_parser.get("官報", "裁判所"))
    announcement_patterns = split_patterns(ini_parser.get("官報", "公告"))
    columns = ini_parser.get("官報", "段組数")
    tesseract_path = ini_parser.get("OCR", "実行ファイル")
    language = ini_parser.get("OCR", "言語")
    psm = ini_parser.get("OCR", "PSM")
    dpi = ini_parser.get("OCR", "解像度")
    intermediate_output = ini_parser.get("OCR", "中間データ出力")
    output_encoding = ini_parser.get("出力", "文字コード")

    if columns < 1:
        raise ValueError("段組数は1以上を指定してください。")

    tesseract = find_tesseract(tesseract_path)
    output_path = pdf_path.with_suffix(".txt")
    ocr_output_path = pdf_path.with_name(pdf_path.stem + "_ocr.txt")

    if intermediate_output not in (0, 1):
        raise ValueError("[OCR] 中間データ出力は0または1を指定してください。")

    print(f"入力PDF : {pdf_path}")
    print(f"INI     : {ini_path}")
    print(f"裁判所  : {', '.join(court_patterns)}")
    print(f"公告    : {', '.join(announcement_patterns)}")
    print(f"段組数  : {columns}")
    print(f"OCR     : {tesseract}")
    print(f"中間データ出力: {intermediate_output}")
    print(f"氏名    : {name if name else '指定なし'}")

    # 全ページを確認し、横向きページ（縦段組み）のみOCRする。
    # 官報では、横向きページを縦段組み、縦向きページを横段組みとして扱う。
    chunks = []
    skipped_portrait_pages = 0
    processed_landscape_pages = 0
    with fitz.open(pdf_path) as document:
        for page_no, page in enumerate(document, start=1):
            # page.rectはページの向きを反映した幅・高さを返す。
            if page.rect.width <= page.rect.height:
                skipped_portrait_pages += 1
                print(
                    f"ページ {page_no}: 縦向き "
                    f"({page.rect.width:.1f} x {page.rect.height:.1f}) のため除外"
                )
                continue

            processed_landscape_pages += 1
            matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)

            # page.rectの座標でclipすると、回転ページでは表示画像との位置がずれる。
            # まずページ全体を回転反映済みの画像として描画し、その画素幅を分割する。
            full_pix = page.get_pixmap(matrix=matrix, alpha=False)
            full_image = Image.frombytes(
                "RGB", (full_pix.width, full_pix.height), full_pix.samples
            )
            pixel_width, pixel_height = full_image.size

            # 固定割合で余白を除外せず、画像内の長い縦罫線から本文左右端を検出する。
            # 右側の余白境界と、左側の日付・官報名・号数欄との境界を線の位置で判定する。
            content_left, content_right = detect_body_horizontal_bounds(full_image, columns)
            content_width = content_right - content_left
            if content_width <= 0:
                raise ValueError(f"ページ {page_no}: 本文領域の幅が不正です。")

            for column_no in range(columns):
                # 左の欄・右余白を除外した本文領域を段数で分割する。
                # 端数は各境界を個別に丸め、隙間や重複を避ける。
                left = content_left + round(column_no * content_width / columns)
                right = content_left + round((column_no + 1) * content_width / columns)
                column_image = full_image.crop((left, 0, right, pixel_height))

                image_path = pdf_path.parent / (
                    f".{pdf_path.stem}_p{page_no:04d}_c{column_no + 1}.png"
                )
                column_image.save(str(image_path))

                try:
                    text = normalize_text(
                        run_tesseract(tesseract, image_path, language, psm)
                    )
                finally:
                    try:
                        image_path.unlink()
                    except OSError:
                        pass

                if text:
                    chunks.append(
                        {
                            "page": page_no,
                            "column": column_no + 1,
                            "text": text,
                        }
                    )

    print(
        f"ページ向き判定: 横向き {processed_landscape_pages} ページを処理、"
        f"縦向き {skipped_portrait_pages} ページを除外"
    )

    # 各段の境界を保持しつつ、OCR文字列を1本の連続ストリームにする。
    # 公告が段やページをまたいでも途中で切らず、次の公告まで保持する。
    stream_parts = []
    positions = []
    cursor = 0

    for chunk in chunks:
        marker = f"\n\n[PAGE={chunk['page']},COLUMN={chunk['column']}]\n"
        start = cursor + len(marker)
        stream_parts.append(marker)
        stream_parts.append(chunk["text"])
        end = start + len(chunk["text"])
        positions.append((start, end, chunk["page"], chunk["column"]))
        cursor = end

    stream = "".join(stream_parts)

    # 中間OCRデータを、入力PDFと同じフォルダーに保存する。
    # ページ・段番号を残すため、検索処理とは独立した確認用データとする。
    if intermediate_output == 1:
        with open(ocr_output_path, "w", encoding=output_encoding) as fp:
            fp.write(f"入力PDF: {pdf_path}\n")
            fp.write("=" * 80 + "\n\n")
            for chunk in chunks:
                fp.write(f"[ページ={chunk['page']}, 段={chunk['column']}]\n")
                fp.write(chunk["text"])
                fp.write("\n\n")
        print(f"中間OCR TXT: {ocr_output_path}")

    # 「次の公告開始」までを現在の公告として保持する。
    raw_records = split_announcements(stream)

    matches = []
    for announcement, body, start_pos, end_pos in raw_records:
        # ANNOUNCEMENT_HEADINGSは「公告の境界」だけを判定する。
        # 実際に抽出する公告はINIの[官報]公告との完全一致で決定する。
        if not announcement_matches_target(announcement, announcement_patterns):
            continue

        matched, court = court_matches(body, court_patterns)
        if not matched:
            continue

        # 氏名は公告全体を対象に検索する。
        if name and name not in body:
            continue

        first_page = ""
        first_column = ""
        for start, end, page_no, column_no in positions:
            if start <= start_pos < end:
                first_page = page_no
                first_column = column_no
                break

        last_page = ""
        last_column = ""
        for start, end, page_no, column_no in positions:
            if start < end_pos <= end or (start_pos < end and end_pos >= end):
                last_page = page_no
                last_column = column_no
                break

        matches.append(
            {
                "announcement": announcement,
                "page": first_page,
                "column": first_column,
                "end_page": last_page,
                "end_column": last_column,
                "court": court,
                "text": body,
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
            fp.write(f"公告: {item['announcement']}\n")
            fp.write(f"開始ページ: {item['page']}\n")
            fp.write(f"開始段: {item['column']}\n")
            fp.write(f"終了ページ: {item['end_page']}\n")
            fp.write(f"終了段: {item['end_column']}\n")
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
            官報をOCRでテキスト化し、
            INIで指定した裁判所と、必要に応じて氏名で抽出します。

            官報掲載項目の固定一覧を公告境界のマスターとして使用し、
            次の段・次のページに続く同一公告は結合します。

            Copyright :{__copyright__}
            author :{__author__}
            """
        ),
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version=f"{SCR_PATH.name} version={__version__}",
    )
    parser.add_argument("input_pdf", help="入力する官報PDF")
    parser.add_argument(
        "-n", "--name",
        help="氏名。指定した場合は裁判所 AND 氏名で絞り込みます。",
    )
    parser.add_argument(
        "-c", "--config",
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
        # -c未指定の既定INIは自動作成する。
        if parsed.config == str(DEFAULT_INI):
            try:
                create_default_ini(ini_path)
            except OSError as e:
                print(f"INIファイルの作成に失敗しました: {ini_path}")
                print(f"ERROR: {e}")
                return NG_VAL
        else:
            print(f"指定されたINIファイルが見つかりません: {ini_path}")
            return NG_VAL

    try:
        return process_pdf(pdf_path, ini_path, parsed.name)
    except Exception as e:
        print(f"ERROR: {e}")
        return NG_VAL


if __name__ == "__main__":
    sys.exit(main())