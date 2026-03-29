# services/pubmed_service.py
# PubMed E-utilities 异步封装：esearch + efetch + XML 解析 + 证据等级排序
# 调用链：esearch（获取 PMID 列表）→ efetch（获取详情 XML）→ 解析 + 证据等级排序

import logging
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

# ── 证据等级映射（值越小优先级越高）────────────────────────────────
_EVIDENCE_RANK: Dict[str, int] = {
    "Practice Guideline": 0,
    "Guideline": 1,
    "Meta-Analysis": 2,
    "Systematic Review": 3,
    "Randomized Controlled Trial": 4,
    "Clinical Trial": 5,
    "Review": 6,
    "Case Reports": 7,
}

# ── NLM 要求所有请求携带 tool 和 email 参数 ──────────────────────
_PUBMED_TOOL = "synapse_md"
_PUBMED_EMAIL = "sophronm91@gmail.com"

# ← 在此填入你申请到的 PubMed API key（有 key = 10 req/s，无 key = 3 req/s）
PUBMED_API_KEY = "0d747a8e235b8974d2b05d74312446f72f08"


class PubMedService:
    """
    PubMed E-utilities 异步封装。

    使用 httpx.AsyncClient 发起异步 HTTP 请求，不阻塞 FastAPI 事件循环。
    对外只暴露 search_papers() 一个方法，内部封装 esearch + efetch + 解析逻辑。
    """

    _BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, api_key: str = PUBMED_API_KEY):
        self.api_key = api_key

    def _common_params(self) -> Dict[str, str]:
        """所有请求都附带的公共参数：tool、email 和可选 api_key。"""
        params: Dict[str, str] = {
            "tool": _PUBMED_TOOL,
            "email": _PUBMED_EMAIL,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    async def search_papers(
        self,
        query: str,
        max_results: int = 5,
        years: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        主入口：用英文检索词搜索 PubMed，返回按证据等级排序的论文列表。

        :param query:       英文检索词（MeSH 术语或自由词组合）
        :param max_results: 最终返回篇数（默认 5）
        :param years:       只检索最近 N 年（默认 3 年）
        :return:            论文列表，失败时返回 []
        """
        try:
            # 多取几倍 PMID，留余量给证据等级过滤
            pmids = await self._esearch(
                query, retmax=max_results * 3, reldays=years * 365
            )
            if not pmids:
                logger.info(f"PubMed 无结果: query={query!r}")
                return []

            # 最多批量取 15 篇详情，避免单次请求过大
            papers = await self._efetch(pmids[:15])

            # 按证据等级排序，截取前 max_results 篇
            papers.sort(key=lambda p: self._evidence_rank(p.get("pub_type", [])))
            return papers[:max_results]

        except Exception as e:
            logger.error(f"PubMed 检索异常: {e}")
            return []

    # ── 内部方法 ────────────────────────────────────────────────────

    async def _esearch(self, query: str, retmax: int, reldays: int) -> List[str]:
        """调用 esearch.fcgi，返回 PMID 字符串列表。"""
        params = {
            **self._common_params(),
            "db": "pubmed",
            "term": query,
            "retmax": str(retmax),
            "sort": "relevance",
            "retmode": "json",
            "datetype": "pdat",
            "reldate": str(reldays),
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self._BASE}/esearch.fcgi", params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("esearchresult", {}).get("idlist", [])

    async def _efetch(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """调用 efetch.fcgi，批量获取论文 XML 并解析。"""
        if not pmids:
            return []
        params = {
            **self._common_params(),
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "xml",
            "retmode": "xml",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{self._BASE}/efetch.fcgi", params=params)
            resp.raise_for_status()
            return self._parse_xml(resp.text)

    def _parse_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """解析 PubMed efetch XML 响应，返回结构化论文列表。"""
        papers: List[Dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"PubMed XML 解析失败: {e}")
            return []

        for article_elem in root.findall(".//PubmedArticle"):
            paper = self._parse_article(article_elem)
            if paper:
                papers.append(paper)
        return papers

    def _parse_article(self, elem) -> Optional[Dict[str, Any]]:
        """从单篇 PubmedArticle 元素提取结构化字段。"""
        try:
            pmid = elem.findtext(".//PMID", "").strip()

            # 标题：itertext 处理内嵌 HTML 标签（<i>、<sup> 等）
            title_elem = elem.find(".//ArticleTitle")
            title = (
                "".join(title_elem.itertext()).strip()
                if title_elem is not None
                else ""
            )

            # 摘要：拼接带 Label 的分段摘要，截断至 500 字
            abstract_parts: List[str] = []
            for ab in elem.findall(".//AbstractText"):
                label = ab.get("Label", "")
                text = "".join(ab.itertext()).strip()
                if not text:
                    continue
                abstract_parts.append(f"{label}: {text}" if label else text)
            full_abstract = " ".join(abstract_parts)
            abstract = full_abstract[:500] + ("..." if len(full_abstract) > 500 else "")

            # 作者：最多展示 3 位，超出显示 et al.
            author_elems = elem.findall(".//Author")
            names: List[str] = []
            for au in author_elems[:3]:
                last = au.findtext("LastName", "")
                initials = au.findtext("Initials", "")
                if last:
                    names.append(f"{last} {initials}".strip())
            author_str = ", ".join(names)
            if len(author_elems) > 3:
                author_str += " et al."

            # 期刊名：优先全名，其次缩写
            journal = (
                elem.findtext(".//Journal/Title")
                or elem.findtext(".//Journal/ISOAbbreviation")
                or ""
            ).strip()

            # 发表日期
            pd_elem = elem.find(".//PubDate")
            if pd_elem is not None:
                year = pd_elem.findtext("Year", "")
                month = pd_elem.findtext("Month", "")
                pub_date = f"{year} {month}".strip()
            else:
                pub_date = ""

            # 文章类型（证据等级依据）
            pub_types = [
                pt.text.strip()
                for pt in elem.findall(".//PublicationType")
                if pt.text
            ]

            if not pmid or not title:
                return None

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": author_str,
                "journal": journal,
                "pub_date": pub_date,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "pub_type": pub_types,
            }

        except Exception as e:
            logger.error(f"解析单篇文章失败: {e}")
            return None

    def _evidence_rank(self, pub_types: List[str]) -> int:
        """返回文章的证据等级排序值，值越小优先级越高。"""
        return min(
            (_EVIDENCE_RANK.get(pt, 8) for pt in pub_types),
            default=8,
        )
