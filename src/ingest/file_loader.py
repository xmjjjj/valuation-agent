"""
从本地文件加载专利文本并构造 PatentData。

支持：
  - .txt / .md：带「标题:」「摘要:」等字段，或无结构全文
  - .json：完整字段或仅元数据（配合同目录同名 .txt）
  - .pdf：提取正文后按 txt 规则解析（需 pypdf）

可选同名的 .meta.json 覆盖/补充元数据（引用次数、IPC 等）。
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from src.models import PatentData
from src.repository import _ipc_prefix

# 字段标签（中英文）
_SECTION_KEYS = {
    "title": ("标题", "专利名称", "名称", "title"),
    "abstract": ("摘要", "技术摘要", "abstract"),
    "claims": ("权利要求", "权利要求书", "claims"),
    "description": ("说明书", "技术方案", "description"),
    "applicant": ("申请人", "applicant"),
    "inventor": ("发明人", "inventor"),
    "ipc_code": ("ipc", "ipc分类", "ipc分类号", "国际专利分类"),
    "patent_id": ("专利号", "申请号", "patent_id", "patent id"),
    "grant_year": ("授权年", "授权年份", "grant_year"),
    "legal_status": ("法律状态", "legal_status"),
    "citation_count": ("被引用次数", "引用次数", "citation_count"),
    "has_award": ("是否获奖", "获奖", "has_award"),
}


def _ascii_temp_copy(path: Path) -> tuple[Path, bool]:
    """
    若路径含中文等非 ASCII 字符，复制到临时英文路径（避免 pypdf/fpdf 的 latin-1 问题）。
    返回 (实际读取路径, 是否需在调用方结束后删除)。
    """
    try:
        str(path).encode("ascii")
        return path, False
    except UnicodeEncodeError:
        suffix = path.suffix.lower() or ".bin"
        fd, tmp_name = tempfile.mkstemp(suffix=suffix, prefix="patent_upload_")
        import os

        os.close(fd)
        tmp = Path(tmp_name)
        shutil.copy2(path, tmp)
        return tmp, True


def _read_text_file(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "读取 PDF 需要安装 pypdf：pip install pypdf"
        ) from exc
    parts: list[str] = []
    with path.open("rb") as fh:
        reader = PdfReader(fh)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    return "\n".join(parts)


def _parse_bool(value: str | bool | int | None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in ("1", "true", "yes", "是", "有", "y")


def _parse_int(value: str | int | None) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    m = re.search(r"\d+", str(value))
    return int(m.group()) if m else None


def _label_line_key(line: str) -> str | None:
    stripped = line.strip()
    for field, labels in _SECTION_KEYS.items():
        for label in labels:
            if re.match(rf"^{re.escape(label)}\s*[:：]\s*", stripped, re.I):
                return field
    return None


def _value_after_colon(line: str) -> str:
    if "：" in line:
        return line.split("：", 1)[1].strip()
    if ":" in line:
        return line.split(":", 1)[1].strip()
    return line.strip()


def _parse_structured_text(text: str) -> dict[str, Any]:
    """解析「字段: 内容」或「字段:\\n多行内容」格式。"""
    data: dict[str, Any] = {}
    current_key: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, current_key
        if current_key and buffer:
            existing = data.get(current_key, "")
            chunk = "\n".join(buffer).strip()
            data[current_key] = f"{existing}\n{chunk}".strip() if existing else chunk
        buffer = []

    for line in text.splitlines():
        key = _label_line_key(line)
        if key:
            flush()
            current_key = key
            inline = _value_after_colon(line)
            if inline:
                buffer = [inline]
            else:
                buffer = []
            continue
        if current_key:
            buffer.append(line)
        elif line.strip() and "title" not in data:
            data.setdefault("_preamble", []).append(line)

    flush()

    if "title" not in data and data.get("_preamble"):
        lines = [ln.strip() for ln in data["_preamble"] if ln.strip()]
        if lines:
            data["title"] = lines[0]
            if len(lines) > 1 and "abstract" not in data:
                data["abstract"] = "\n".join(lines[1:])
    data.pop("_preamble", None)

    return data


def _merge_dict(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in extra.items():
        if v is not None and v != "":
            out[k] = v
    return out


def _load_meta_json(path: Path) -> dict[str, Any]:
    candidates = [
        path.with_suffix(".meta.json"),
        path.parent / f"{path.stem}.meta.json",
    ]
    if path.suffix.lower() == ".json" and path.name.endswith(".meta.json"):
        return {}
    for meta in candidates:
        if meta.is_file() and meta.resolve() != path.resolve():
            return json.loads(_read_text_file(meta))
    return {}


def _load_json_document(path: Path) -> dict[str, Any]:
    raw = json.loads(_read_text_file(path))
    if not isinstance(raw, dict):
        raise ValueError("JSON 文件根节点必须是对象 {...}")
    return raw


def _dict_to_patent_data(data: dict[str, Any], source: Path) -> PatentData:
    title = str(data.get("title") or data.get("专利名称") or source.stem).strip()
    abstract = str(data.get("abstract") or data.get("摘要") or "").strip()
    claims = str(data.get("claims") or data.get("权利要求") or "").strip()
    description = str(data.get("description") or data.get("说明书") or "").strip()

    if not abstract and description:
        abstract = description[:8000]
    if not abstract and not claims:
        body = str(data.get("body") or data.get("text") or data.get("content") or "").strip()
        if body:
            abstract = body[:12000]
    if not claims and description and description != abstract:
        claims = description[:12000]

    ipc_code = str(data.get("ipc_code") or data.get("ipc") or "C07").strip()
    prefix = _ipc_prefix(ipc_code)
    raw_id = data.get("patent_id") or data.get("专利号")
    if raw_id:
        patent_id = str(raw_id).strip()
    else:
        digest = hashlib.sha256(source.name.encode("utf-8")).hexdigest()[:12]
        patent_id = f"FILE-{digest}"

    industry = data.get("industry")
    if isinstance(industry, dict):
        industry = dict(industry)
    else:
        industry = None

    return PatentData(
        patent_id=patent_id,
        title=title,
        abstract=abstract,
        claims=claims,
        applicant=str(data.get("applicant") or data.get("申请人") or "").strip(),
        inventor=str(data.get("inventor") or data.get("发明人") or "").strip(),
        ipc_code=ipc_code,
        ipc_prefix=prefix,
        grant_year=_parse_int(data.get("grant_year") or data.get("授权年份")),
        legal_status=str(data.get("legal_status") or data.get("法律状态") or "有效").strip(),
        citation_count=int(_parse_int(data.get("citation_count")) or 0),
        has_award=_parse_bool(data.get("has_award") or data.get("是否获奖")),
        avg_citation=float(data.get("avg_citation") or 5.0),
        is_ipc_frontier=_parse_bool(data.get("is_ipc_frontier")),
        industry=industry,
    )


def _llm_extract_fields(raw_text: str) -> dict[str, Any] | None:
    from src.llm.client import api_key_is_usable, chat_completion_json

    if not api_key_is_usable() or len(raw_text.strip()) < 80:
        return None

    messages = [
        {
            "role": "system",
            "content": (
                "你是专利文献解析助手。从用户给出的专利相关材料中提取结构化字段。"
                "只返回合法 JSON，缺失字段用空字符串。"
            ),
        },
        {
            "role": "user",
            "content": (
                "提取字段：title, abstract, claims, ipc_code, applicant, inventor。\n"
                f"材料全文（可截断）：\n{raw_text[:12000]}\n\n"
                '输出 JSON 示例：{"title":"","abstract":"","claims":"","ipc_code":"C07C",'
                '"applicant":"","inventor":""}'
            ),
        },
    ]
    data = chat_completion_json(messages)
    return data if isinstance(data, dict) else None


def load_patent_from_file(path: str | Path, *, use_llm: bool = True) -> PatentData:
    """
    从本地文件加载 PatentData。

    :param path: .txt / .md / .json / .pdf
    :param use_llm: 字段缺失时是否尝试 LLM 抽取（需配置 API Key）
    """
    file_path = Path(path).resolve()
    if not file_path.is_file():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    read_path, is_temp = _ascii_temp_copy(file_path)
    suffix = read_path.suffix.lower()
    raw_document = ""
    try:
        merged: dict[str, Any] = {}

        if suffix == ".json":
            merged = _load_json_document(read_path)
            txt_sibling = file_path.with_suffix(".txt")
            if txt_sibling.is_file():
                merged = _merge_dict(
                    _parse_structured_text(_read_text_file(txt_sibling)), merged
                )
        elif suffix == ".pdf":
            raw_document = _read_pdf(read_path)
            merged = _parse_structured_text(raw_document)
        else:
            raw_document = _read_text_file(read_path)
            merged = _parse_structured_text(raw_document)

        merged = _merge_dict(merged, _load_meta_json(file_path))

        patent = _dict_to_patent_data(merged, file_path)

        if use_llm and (not patent.abstract or len(patent.title) < 4):
            raw = raw_document or (
                patent.abstract if suffix == ".json" else _read_text_file(read_path)
            )
            llm_fields = _llm_extract_fields(raw or patent.abstract)
            if llm_fields:
                patent = _dict_to_patent_data(_merge_dict(merged, llm_fields), file_path)

        if not patent.abstract:
            raise ValueError(
                "未能从文件中解析出摘要/正文。请使用「标题:」「摘要:」「权利要求:」"
                "格式，或提供 JSON，参见 samples/patent_example.txt；"
                "若 PDF 为扫描图片版，需先 OCR 或改为 txt。"
            )

        return patent
    finally:
        if is_temp:
            try:
                read_path.unlink(missing_ok=True)
            except OSError:
                pass
