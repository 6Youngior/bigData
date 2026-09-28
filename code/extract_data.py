"""从原始压缩包提取九个 Excel 工作簿。"""

from pathlib import Path
from shutil import copyfileobj
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "数据.zip"
DESTINATION = ROOT / "data" / "数据"

with ZipFile(ARCHIVE, metadata_encoding="utf-8") as archive:
    workbooks = [
        item for item in archive.infolist()
        if item.filename.startswith("数据/")
        and item.filename.endswith(".xlsx")
        and "/" not in item.filename[len("数据/"):]
    ]
    if len(workbooks) != 9:
        raise ValueError(f"Expected 9 Excel workbooks, found {len(workbooks)}")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for item in workbooks:
        with archive.open(item) as source, (DESTINATION / Path(item.filename).name).open("wb") as target:
            copyfileobj(source, target)

print(f"Extracted {len(workbooks)} workbooks to {DESTINATION}")
