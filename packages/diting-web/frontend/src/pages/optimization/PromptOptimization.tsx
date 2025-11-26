import { useState } from "react";

interface OptimizationResult {
  original: string;
  optimized: string;
  improvements: string[];
  score: {
    clarity: number;
    specificity: number;
    effectiveness: number;
  };
}

export default function PromptOptimization() {
  const [originalPrompt, setOriginalPrompt] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [targetModel, setTargetModel] = useState("gpt-4");
  const [optimizationGoal, setOptimizationGoal] = useState<string[]>([]);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [result, setResult] = useState<OptimizationResult | null>(null);

  const goals = [
    { id: "clarity", label: "提高清晰度", icon: "🎯" },
    { id: "specificity", label: "增强具体性", icon: "📝" },
    { id: "examples", label: "添加示例", icon: "💡" },
    { id: "structure", label: "优化结构", icon: "🏗️" },
    { id: "constraints", label: "添加约束", icon: "🔒" },
  ];

  const handleOptimize = async () => {
    if (!originalPrompt.trim()) return;

    setIsOptimizing(true);
    
    // 模拟API调用
    setTimeout(() => {
      setResult({
        original: originalPrompt,
        optimized: `You are an expert question-answering system evaluator with deep knowledge of NLP and machine learning.

Your task is to systematically assess generated answers using the following structured criteria:

## Evaluation Framework

1. **Factual Correctness** (0-1 score)
   - Verify all claims against the provided context
   - Check for any hallucinations or unsupported statements
   - Assess logical coherence

2. **Completeness** (0-1 score)
   - Does the answer fully address all parts of the question?
   - Are there any missing critical details?
   - Is the depth of explanation appropriate?

3. **Relevance** (0-1 score)
   - Is every part of the answer directly related to the question?
   - Are there any tangential or off-topic elements?

## Instructions
- Provide individual scores for each criterion
- Justify your scores with specific references
- Use a consistent scoring rubric
- Be objective and unbiased

## Input Format
Question: {question}
Context: {context}
Generated Answer: {answer}

## Output Format
Return your evaluation as a JSON object with scores and explanations.`,
        improvements: [
          "添加了明确的角色定义，使AI理解其专业领域",
          "将评估标准结构化，使用编号列表提高清晰度",
          "为每个标准添加了详细的评估要点",
          "明确了输入输出格式，减少歧义",
          "添加了具体的评分指导原则"
        ],
        score: {
          clarity: 0.92,
          specificity: 0.88,
          effectiveness: 0.90
        }
      });
      setIsOptimizing(false);
    }, 2000);
  };

  const toggleGoal = (goalId: string) => {
    setOptimizationGoal(prev =>
      prev.includes(goalId)
        ? prev.filter(id => id !== goalId)
        : [...prev, goalId]
    );
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // 可以添加toast提示
  };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Left: Input */}
        <div className="space-y-5">
          {/* Original Prompt */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-2">
              原始提示词 <span className="text-red-500">*</span>
            </label>
            <textarea
              value={originalPrompt}
              onChange={(e) => setOriginalPrompt(e.target.value)}
              placeholder="输入您想要优化的提示词..."
              className="textarea textarea-bordered w-full h-48 font-mono text-sm"
            />
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-gray-500">
                {originalPrompt.length} 字符
              </span>
              <button
                onClick={() => setOriginalPrompt("")}
                className="text-xs text-gray-500 hover:text-gray-700"
              >
                清空
              </button>
            </div>
          </div>

          {/* Task Description */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-2">
              任务描述
            </label>
            <textarea
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              placeholder="描述这个提示词的用途和目标..."
              className="textarea textarea-bordered w-full h-24 text-sm"
            />
          </div>

          {/* Configuration */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-900 mb-2">
                目标模型
              </label>
              <select
                value={targetModel}
                onChange={(e) => setTargetModel(e.target.value)}
                className="select select-bordered w-full"
              >
                <option value="gpt-4">GPT-4</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                <option value="claude-3">Claude 3</option>
                <option value="gemini-pro">Gemini Pro</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-900 mb-3">
                优化目标
              </label>
              <div className="grid grid-cols-2 gap-2">
                {goals.map((goal) => (
                  <button
                    key={goal.id}
                    onClick={() => toggleGoal(goal.id)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all border-2 ${
                      optimizationGoal.includes(goal.id)
                        ? "border-pink-500 bg-pink-50 text-pink-700"
                        : "border-gray-200 bg-white text-gray-700 hover:border-pink-300"
                    }`}
                  >
                    <span>{goal.icon}</span>
                    <span>{goal.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Action Button */}
          <button
            onClick={handleOptimize}
            disabled={!originalPrompt.trim() || isOptimizing}
            className="btn btn-primary w-full gap-2"
          >
            {isOptimizing ? (
              <>
                <span className="loading loading-spinner loading-sm"></span>
                优化中...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                开始优化
              </>
            )}
          </button>
        </div>

        {/* Right: Result */}
        <div>
          {result ? (
            <div className="space-y-4">
              {/* Score Cards */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-white rounded-lg border border-gray-200 p-3 text-center">
                  <div className="text-xs text-gray-600 mb-1">清晰度</div>
                  <div className="text-2xl font-bold text-pink-600">
                    {(result.score.clarity * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-3 text-center">
                  <div className="text-xs text-gray-600 mb-1">具体性</div>
                  <div className="text-2xl font-bold text-purple-600">
                    {(result.score.specificity * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-3 text-center">
                  <div className="text-xs text-gray-600 mb-1">有效性</div>
                  <div className="text-2xl font-bold text-blue-600">
                    {(result.score.effectiveness * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* Optimized Prompt */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-900">优化后的提示词</h3>
                  <button
                    onClick={() => copyToClipboard(result.optimized)}
                    className="btn btn-ghost btn-xs gap-1"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    复制
                  </button>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 border border-gray-200 max-h-96 overflow-y-auto">
                  <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
                    {result.optimized}
                  </pre>
                </div>
              </div>

              {/* Improvements */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">改进点</h3>
                <ul className="space-y-2">
                  {result.improvements.map((improvement, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm">
                      <svg className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-gray-700">{improvement}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <button className="btn btn-outline flex-1" onClick={() => setOriginalPrompt(result.optimized)}>
                  继续优化
                </button>
                <button className="btn btn-primary flex-1">
                  保存到仓库
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-12 text-center h-full flex items-center justify-center">
              <div>
                <svg className="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">准备开始优化</h3>
                <p className="text-gray-500 text-sm">输入原始提示词并点击"开始优化"</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* History */}
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">优化历史</h3>
        <div className="space-y-3">
          {[
            { task: "QA 评估提示词优化", score: 0.92, time: "10分钟前" },
            { task: "对话系统提示词优化", score: 0.88, time: "1小时前" },
            { task: "数据合成提示词优化", score: 0.85, time: "3小时前" },
          ].map((item, idx) => (
            <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-900">{item.task}</div>
                <div className="text-xs text-gray-500">{item.time}</div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-sm font-semibold text-pink-600">
                  {(item.score * 100).toFixed(0)}%
                </div>
                <button className="btn btn-ghost btn-xs">查看</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

