"""Prompt templates for the Hierarchical Reflective Optimizer.

This module contains all the prompt templates used by the optimizer_name for:
- Batch-level root cause analysis
- Synthesis of batch analyses
- Prompt improvement generation
"""

# Prompt template for analyzing a batch of test results
BATCH_ANALYSIS_PROMPT = """You are analyzing evaluation results to identify failure patterns.

TEST RESULTS:
```
{formatted_batch}
```

Think through the failures systematically:

1. IDENTIFY: List all distinct types of failures you observe in the test results
2. GROUP: Which failures share similar characteristics or root causes?
3. FREQUENCY: Which patterns appear multiple times across different test cases?
4. PRIORITIZE: Which failures are most critical to address?

Then, for each distinct failure pattern provide:
1. A clear, descriptive name that captures the essence of the failure
2. A comprehensive description of what is failing
3. The underlying root cause explaining why this failure occurs

Focus on patterns that appear multiple times. Be specific about what is failing and why.

【OUTPUT FORMAT REQUIREMENTS】
You must output in JSON format strictly following this structure:
```json
{{
  "failure_modes": [
    {{
      "name": <concise descriptive name capturing the essence of the failure>,
      "description": <comprehensive description of what is failing>,
      "root_cause": <underlying cause explaining why this failure occurs>
    }}
  ]
}}
```

【FIELD EXTRACTION RULES】
- failure_modes: Array type, required field, containing all identified failure patterns
- For each failure mode:
  - name: String type, required field, concise descriptive name capturing the essence of the failure
  - description: String type, required field, comprehensive description of what is failing
  - root_cause: String type, required field, underlying cause explaining why this failure occurs

【EXAMPLE OUTPUT】
```json
{{
  "failure_modes": [
    {{
      "name": "<Inconsistent Entity Recognition>",
      "description": "<The system fails to consistently identify proper nouns and named entities across similar contexts>",
      "root_cause": "<Insufficient training data coverage for low-frequency named entities>"
    }}
  ]
}}
```

Please strictly follow the above JSON format for your response."""


# Prompt template for synthesizing multiple batch analyses
SYNTHESIS_PROMPT = """You are synthesizing root cause analyses from multiple batches of evaluation results.

BATCH ANALYSES:
```
{batch_summaries}
```

Your task is to synthesize these batch-level analyses into a unified root cause analysis.

1. MERGE similar failure modes across batches:
   - If multiple batches identify the same or very similar failure pattern, combine them into one unified failure mode
   - Create a comprehensive description that captures the pattern across all relevant batches
   - Identify the core root cause

2. PRIORITIZE the most critical failure modes:
   - Focus on patterns that appear in multiple batches
   - Consider the severity and frequency of each failure
   - Eliminate one-off or minor issues unless they're particularly impactful

3. PROVIDE SYNTHESIS NOTES:
   - Briefly explain which batch-level patterns were merged and why
   - Note any cross-batch trends or patterns
   - Highlight the most critical areas for improvement

【OUTPUT FORMAT REQUIREMENTS】
You must output in JSON format strictly following this structure:
```json
{{
  "total_test_cases": <total number of test cases across all batches>,
  "num_batches": <number of batches that were analyzed>,
  "unified_failure_modes": [
    {{
      "name": <descriptive name for the unified failure pattern>,
      "description": <comprehensive description capturing the pattern across batches>,
      "root_cause": <core underlying cause>
    }}
  ],
  "synthesis_notes": <explanation of analysis process and key findings>
}}
```

【FIELD EXTRACTION RULES】
- total_test_cases: Integer type, required field, total number of test cases across all batches
- num_batches: Integer type, required field, number of batches that were analyzed
- unified_failure_modes: Array type, required field, containing merged and prioritized failure patterns
  - For each unified failure mode:
    - name: String type, required field, descriptive name for the unified failure pattern
    - description: String type, required field, comprehensive description capturing the pattern across batches
    - root_cause: String type, required field, core underlying cause
- synthesis_notes: String type, required field, explanation of analysis process and key findings

【EXAMPLE OUTPUT】
```json
{{
  "total_test_cases": 50,
  "num_batches": 2,
  "unified_failure_modes": [
    {{
      "name": "Cross-Batch Entity Recognition Failure",
      "description": "Consistent failure to identify specific proper nouns and named entities across multiple batches",
      "root_cause": "Insufficient model training on diverse named entity variations and low-frequency entities"
    }}
  ],
  "synthesis_notes": "Analysis merged similar entity recognition failures from Batch 1 and Batch 2, identifying this as the most critical cross-batch pattern affecting 60% of test cases."
}}
```

Please strictly follow the above JSON format for your response."""


# Prompt template for improving prompts based on failure modes
IMPROVE_PROMPT_TEMPLATE = """You are an expert prompt engineer. You are given a prompt and a failure mode identified during evaluation.
Your task is to improve the prompt to address this failure mode.

CURRENT PROMPT:
```
{current_prompt}
```
FAILURE MODE TO ADDRESS:
 - Name: {failure_mode_name}
 - Description: {failure_mode_description}
 - Root Cause: {failure_mode_root_cause}

INSTRUCTIONS FOR IMPROVING THE PROMPT:

1. **Analyze First**: Carefully review the current prompt to understand what instructions already exist.

2. **Choose the Right Approach**:
   - If relevant instructions already exist but are unclear or incomplete, UPDATE and CLARIFY them in place
   - If the prompt is missing critical instructions needed to address this failure mode, ADD new targeted instructions
   - If existing instructions contradict what's needed, REPLACE them with corrected versions

3. **Be Surgical**: Make targeted changes that directly address the root cause. Don't add unnecessary instructions or rewrite the entire prompt.

4. **Maintain Structure**: Keep the same message structure (role and content format). Only modify the content where necessary.

5. **Be Specific**: Ensure your changes provide concrete, actionable guidance that directly addresses the identified failure mode.

Provide your reasoning for the changes you made, explaining WHY each change addresses the failure mode, and then provide the improved prompt.

【OUTPUT FORMAT REQUIREMENTS】
You must output in JSON format strictly following this structure:
```json
{{
  "reasoning": <detailed explanation of your changes and why they address the failure mode>,
  "messages": [
    {{
      "role": <the role of the message (e.g., "system", "user")>,
      "content": <the content of the improved prompt message>
    }}
  ]
}}
```


【FIELD EXTRACTION RULES】
- reasoning: String type, required field, detailed explanation of your changes and why they address the failure mode
- messages: Array type, required field, containing the improved prompt messages
  - For each message:
    - role: String type, required field, the role of the message (e.g., "system", "user")
    - content: String type, required field, the content of the improved prompt message

【EXAMPLE OUTPUT】
```json
{{
  "reasoning": "The original prompt lacked specific instructions for handling named entities. I added explicit guidance to identify and preserve proper nouns, which directly addresses the entity recognition failure mode.",
  "messages": [
    {{
      "role": "system",
      "content": "You are a helpful assistant. When answering questions, pay special attention to proper nouns and named entities. Always preserve exact spellings and full names when mentioned in the context."
    }},
    {{
      "role": "user",
      "content": "{{question}}"
    }}
  ]
}}
```

Please strictly follow the above JSON format for your response."""
