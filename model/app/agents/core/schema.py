"""统一数据模型"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class ClinicalContext(BaseModel):
    """临床上下文"""
    基本信息: Dict = Field(default_factory=dict)
    起病方式: str = ""
    主要症状: List[str] = Field(default_factory=list)
    神经系统查体: Dict = Field(default_factory=dict)
    意识水平: str = ""
    生命体征: Dict = Field(default_factory=dict)
    既往史: List[str] = Field(default_factory=list)
    用药史: List[str] = Field(default_factory=list)
    危险因素: List[str] = Field(default_factory=list)
    非卒中线索: List[str] = Field(default_factory=list)


class ClinicalState(BaseModel):
    """临床状态（用于 LangGraph）"""
    case_text: str = ""
    all_info: str = ""
    report_mode: str = "emergency"
    intent_type: str = ""
    context: Dict = Field(default_factory=dict)
    clinical_questions: List[str] = Field(default_factory=list)
    key_risks: List[str] = Field(default_factory=list)
    complexity: str = "high"
    evidence: str = ""
    proposal: str = ""
    critique: str = ""
    user_questions: List[str] = Field(default_factory=list)
    report: str = ""
