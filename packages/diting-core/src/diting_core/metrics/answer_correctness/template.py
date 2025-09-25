#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List
import json
from diting_core.metrics.answer_correctness.schema import Verdicts, Statements, Reason
from diting_core.metrics.utils import Language


class AnswerCorrectnessTemplate:
    @staticmethod
    def generate_statements(
        user_input: str, text: str, language: Language = Language.ENGLISH
    ) -> str:
        template_zh = f"""给定一个问题和答案，分析答案中每个句子的复杂性。将每个句子分解为一个或多个完全可理解的陈述。确保在任何陈述中都不使用代词。以JSON格式输出。

请返回符合以下JSON Schema格式的输出：
{json.dumps(Statements.model_json_schema(), ensure_ascii=False)}
不要使用单引号，使用双引号并正确转义。

--------示例-----------
示例 1
输入: {{
    "question": "阿尔伯特·爱因斯坦是谁，他最著名的贡献是什么？",
    "answer": "他是一位德国出生的理论物理学家，被广泛认为是有史以来最伟大、最有影响力的物理学家之一。他最著名的贡献是发展了相对论理论，他还对量子力学理论的发展做出了重要贡献。"
}}
输出: {{
    "statements": [
        "阿尔伯特·爱因斯坦是一位德国出生的理论物理学家。",
        "阿尔伯特·爱因斯坦被认为是有史以来最伟大、最有影响力的物理学家之一。",
        "阿尔伯特·爱因斯坦最著名的贡献是发展了相对论理论。",
        "阿尔伯特·爱因斯坦还对量子力学理论的发展做出了重要贡献。"
    ]
}}
-----------------------------

现在对以下输入执行相同操作
输入: {{
    "question": "{user_input}",
    "answer": "{text}"
}}
输出: """

        template_en = f"""Given a question and an answer, analyze the complexity of each sentence in the answer. Break down each sentence into one or more fully understandable statements. Ensure that no pronouns are used in any statement. Format the outputs in JSON.

Please return the output in a JSON format that complies with the following schema as specified in JSON Schema:
{json.dumps(Statements.model_json_schema())}
Do not use single quotes in your response but double quotes, properly escaped with a backslash.

--------EXAMPLES-----------
Example 1
Input: {{
    "question": "Who was Albert Einstein and what is he best known for?",
    "answer": "He was a German-born theoretical physicist, widely acknowledged to be one of the greatest and most influential physicists of all time. He was best known for developing the theory of relativity, he also made important contributions to the development of the theory of quantum mechanics."
}}
Output: {{
    "statements": [
        "Albert Einstein was a German-born theoretical physicist.",
        "Albert Einstein is recognized as one of the greatest and most influential physicists of all time.",
        "Albert Einstein was best known for developing the theory of relativity.",
        "Albert Einstein also made important contributions to the development of the theory of quantum mechanics."
    ]
}}
-----------------------------

Now perform the same with the following input
input: {{
    "question": "{user_input}",
    "answer": "{text}"
}}
Output: """

        return template_zh if language == Language.CHINESE else template_en

    @staticmethod
    def generate_verdicts(
        user_input: str,
        actual_output_statements: List[str],
        expected_output_statements: list[str],
        language: Language = Language.ENGLISH,
    ) -> str:
        template_zh = f"""给定一个标准答案(expected_answer)和实际答案(answer)的陈述，分析每个陈述并将其分类为以下类别之一：TP（真正例）：实际答案中存在且得到标准答案中一个或多个陈述直接支持的陈述，FP（假正例）：实际答案中存在但标准答案中没有直接支持的陈述，FN（假负例）：标准答案中存在但实际答案中没有的陈述。每个陈述只能属于一个类别。为每个分类提供原因。

请返回符合以下JSON Schema格式的输出：
{json.dumps(Verdicts.model_json_schema(), ensure_ascii=False)}
不要使用单引号，使用双引号并正确转义。

--------示例-----------
示例 1
输入: {{
    "question": "什么是水的沸点？",
    "answer": [
        "水在海平面的沸点是100摄氏度"
    ],
    "expected_answer": [
        "水在海平面的沸点是100摄氏度（212华氏度）。",
        "水的沸点会随海拔高度变化。"
    ]
}}
输出: {{
    "TP": [
        {{
            "statement": "水在海平面的沸点是100摄氏度",
            "reason": "这个陈述得到标准答案的直接支持，标准答案明确指出水在海平面的沸点是100摄氏度。"
        }}
    ],
    "FP": [],
    "FN": [
        {{
            "statement": "水的沸点会随海拔高度变化。",
            "reason": "答案中没有提到这个关于水沸点随海拔变化的重要信息。"
        }}
    ]
}}
-----------------------------

现在对以下输入执行相同操作
输入: {{
    "question": "{user_input}",
    "answer": {actual_output_statements},
    "expected_answer": {expected_output_statements}
}}
输出: """

        template_en = f"""Given an expected answer and actual answer statements, analyze each statement and classify them in one of the following categories: TP (true positive): statements that are present in actual answer that are also directly supported by the one or more statements in expected answer, FP (false positive): statements present in the actual answer but not directly supported by any statement in expected answer, FN (false negative): statements found in the expected answer but not present in actual answer. Each statement can only belong to one of the categories. Provide a reason for each classification.

Please return the output in a JSON format that complies with the following schema as specified in JSON Schema:
{json.dumps(Verdicts.model_json_schema())}
Do not use single quotes in your response but double quotes, properly escaped with a backslash.

--------EXAMPLES-----------
Example 1
Input: {{
    "question": "What is the boiling point of water?",
    "answer": [
        "The boiling point of water is 100 degrees Celsius at sea level"
    ],
    "expected_answer": [
        "The boiling point of water is 100 degrees Celsius (212 degrees Fahrenheit) at sea level.",
        "The boiling point of water can change with altitude."
    ]
}}
Output: {{
    "TP": [
        {{
            "statement": "The boiling point of water is 100 degrees Celsius at sea level",
            "reason": "This statement is directly supported by the expected answer which specifies the boiling point of water as 100 degrees Celsius at sea level."
        }}
    ],
    "FP": [],
    "FN": [
        {{
            "statement": "The boiling point of water can change with altitude.",
            "reason": "This additional information about how the boiling point of water can vary with altitude is not mentioned in the answer."
        }}
    ]
}}
-----------------------------

Now perform the same with the following input
input: {{
    "question": "{user_input}",
    "answer": {actual_output_statements},
    "expected_answer": {expected_output_statements}
}}
Output: """

        return template_zh if language == Language.CHINESE else template_en

    @staticmethod
    def generate_reasons(
        score: float,
        tp_reasons: List[str],
        fp_reasons: List[str],
        fn_reasons: List[str],
        language: Language = Language.ENGLISH,
    ) -> str:
        template_zh = f"""基于答案正确性评分和TP、FP、FN的原因列表：
- **正确包含 (TP)**: 回答中事实准确且有事实依据支持的陈述
- **错误添加 (FP)**: 回答中缺乏事实依据支持的陈述
- **遗漏 (FN)**: 事实依据中存在但回答中缺失的重要事实
这些分类仅用于分析。生成解释时，不要使用"TP"、"FP"、"FN"、"真正例"等技术术语。不要在原因中包含数字分数。请用通俗易懂的自然语言提供简洁友好的原因。
如果分数为1，请保持简短并用积极鼓励的语调。

请返回符合以下JSON Schema格式的输出：
{json.dumps(Reason.model_json_schema(), ensure_ascii=False)}
不要使用单引号，使用双引号并正确转义。

示例JSON：
{{
    "reason": "<你的原因>"
}}

-----------------------------

现在对以下输入执行相同操作
输入: {{
    "answer_correctness_score": {score},
    "tp_reasons": {tp_reasons},
    "fp_reasons": {fp_reasons},
    "fn_reasons": {fn_reasons},
}}
输出: """

        template_en = f"""Given the answer correctness score, the list of reasons of TP, FP, FN:
- **Correctly Included (TP)**: Statements in the response that are factually accurate and directly supported by the expected answer.
- **Incorrectly Added (FP)**: Statements in the response that are not supported by the expected answer.
- **Missing (FN)**: Important facts present in the expected answer but absent from the response.
These categories are for analysis only. When generating your explanation, do NOT use the terms "TP", "FP", "FN", "true positive",
or any technical evaluation jargon. Do NOT include the numeric score in your reason. Provide a concise and user-friendly reason using plain, natural language.

IMPORTANT: Provide your reason in the SAME LANGUAGE as the input. If the input is in Chinese, respond in Chinese. If the input is in English, respond in English.

Please return the output in a JSON format that complies with the following schema as specified in JSON Schema:
{json.dumps(Reason.model_json_schema())}
Do not use single quotes in your response but double quotes, properly escaped with a backslash.

Example JSON:
{{
    "reason": "<your_reason>"
}}

If the score is 1, keep it short and say something positive with an upbeat encouraging tone (but don't overdo it).
-----------------------------

Now perform the same with the following input
input: {{
    "answer_correctness_score": {score},
    "tp_reasons": {tp_reasons},
    "fp_reasons": {fp_reasons},
    "fn_reasons": {fn_reasons},
}}
Output: """

        return template_zh if language == Language.CHINESE else template_en
