import logging
from app.agents.services.query_service import QueryGenerationService
from app.agents.services.retrieval_service import EvidenceRetrievalService
from app.agents.services.synthesis_service import EvidenceSynthesisService

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG 管道，组装查询生成、证据检索、证据合成服务"""

    def __init__(
        self,
        query_gen: QueryGenerationService,
        retrieval: EvidenceRetrievalService,
        synthesis: EvidenceSynthesisService
    ):
        self.query_gen = query_gen
        self.retrieval = retrieval
        self.synthesis = synthesis

    def run(self, question: str) -> str:
        """执行 RAG 管道"""
        try:
            logger.info(f"RAGPipeline start: {question[:60]}")
            
            # 1. 生成检索查询
            queries = self.query_gen.generate(question)
            logger.info(f"Generated queries: {queries}")
            
            # 2. 并行检索证据
            evidence = self.retrieval.parallel_retrieve(queries)
            if not evidence:
                return "未检索到相关医学文献。"
            
            # 3. 合成证据
            result = self.synthesis.synthesize(question, evidence)
            logger.info(f"RAGPipeline completed")
            
            return result
            
        except Exception as e:
            logger.error(f"RAGPipeline error: {e}")
            return "证据层运行异常。"
