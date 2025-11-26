# 前端评估维度功能集成说明

## ✅ 完成状态

前端评估维度管理页面已**完全对接后端新 API**，支持创建、编辑、删除自定义维度。

## 🎯 主要功能

### 1. **查看维度列表**
- ✅ 显示总维度、内置维度、自定义维度的统计
- ✅ 按类型筛选（全部/内置/自定义）
- ✅ 搜索维度（按名称、描述）
- ✅ 区分内置和自定义维度的标签

### 2. **创建自定义维度** 
- ✅ 点击"创建维度"按钮打开对话框
- ✅ 仅需填写三要素：
  - 名称（必填）
  - 描述（可选）
  - 提示词（可选）
- ✅ 自动设置为 CUSTOM 类型
- ✅ 创建成功后刷新列表

### 3. **编辑自定义维度**
- ✅ 仅自定义维度显示"编辑"按钮
- ✅ 支持修改名称、描述、提示词
- ✅ 内置维度不可编辑

### 4. **删除自定义维度**
- ✅ 仅自定义维度显示"删除"按钮
- ✅ 删除前确认提示
- ✅ 内置维度不可删除

## 📁 修改的文件

### 后端
无需修改，API 已就绪

### 前端

#### 1. `src/types/api.ts`
更新类型定义：
```typescript
// 新增枚举
export enum EvalMetricTypeEnum {
  BUILTIN = "builtin",
  CUSTOM = "custom",
}

// 简化创建接口 - 只需三要素
export interface MetricCreate {
  name: string;         // 必填
  description?: string; // 可选
  prompt?: string;      // 可选
}

// 简化更新接口
export interface MetricUpdate {
  name?: string;
  description?: string;
  prompt?: string;
}

// 更新响应接口
export interface MetricResponse {
  id: string;
  name: string;
  description: string | null;
  type: EvalMetricTypeEnum;      // 新字段
  prompt: string | null;          // 新字段
  user_input_required: boolean;   // 新字段
  actual_output_required: boolean;
  expected_output_required: boolean;
  context_required: boolean;
  retrieval_context_required: boolean;
  embedding_required: boolean;
  llm_required: boolean;
  created_at: string;
  updated_at: string;
}
```

#### 2. `src/api/client.ts`
更新 API 调用：
```typescript
// 更新导入
import { EvalMetricTypeEnum } from "@/types/api";

// 更新 getMetrics 参数
export async function getMetrics(
  page: number = 1,
  pageSize: number = 20,
  metricType?: EvalMetricTypeEnum  // 新参数
): Promise<PaginatedResponse<MetricResponse>>
```

#### 3. `src/pages/evaluation/MetricManagement.tsx`
**完全重写**，主要变更：

**状态管理：**
```typescript
const [showCreateModal, setShowCreateModal] = useState(false);
const [showEditModal, setShowEditModal] = useState(false);
const [editingMetric, setEditingMetric] = useState<MetricResponse | null>(null);
const [formData, setFormData] = useState<MetricCreate>({
  name: "",
  description: "",
  prompt: "",
});
```

**新增功能函数：**
- `handleCreateMetric()` - 创建维度
- `handleEditMetric()` - 编辑维度
- `handleDeleteMetric()` - 删除维度
- `openEditModal()` - 打开编辑对话框

**UI 更新：**
- 使用 `metric.type` 替代 `metric.is_builtin`
- 使用 `metric.name` 替代 `metric.display_name`
- 移除 `metric.category`、`metric.default_config`、`metric.usage_count`
- 显示 `metric.prompt` 字段
- 添加创建/编辑模态框
- 仅自定义维度显示编辑/删除按钮

## 🚀 使用流程

### 创建自定义维度
1. 点击右上角"创建维度"按钮
2. 填写表单：
   - 名称（必填）：例如 `custom_accuracy`
   - 描述（可选）：维度说明
   - 提示词（可选）：评估用的 prompt
3. 点击"创建"
4. 自动刷新列表

### 编辑自定义维度
1. 找到自定义维度卡片
2. 点击"编辑"按钮
3. 修改表单内容
4. 点击"保存"

### 删除自定义维度
1. 找到自定义维度卡片
2. 点击"删除"按钮
3. 确认删除

## 📸 界面效果

### 维度卡片
- **内置维度**：蓝色标签 "内置"，无操作按钮
- **自定义维度**：橙色标签 "自定义"，有"编辑"和"删除"按钮

### 创建对话框
- 标题：创建自定义维度
- 三个输入框：名称、描述、提示词
- 按钮：取消、创建

### 编辑对话框
- 标题：编辑自定义维度
- 预填充现有数据
- 按钮：取消、保存

## ⚠️ 注意事项

1. **内置维度不可操作**：内置维度（type=builtin）只能查看，不能编辑或删除
2. **名称必填**：创建/编辑时，名称字段为必填项
3. **自动刷新**：创建、编辑、删除成功后会自动刷新列表
4. **错误提示**：操作失败时会弹出 alert 提示错误信息

## 🔗 API 对接说明

前端调用的后端 API：
- `GET /api/v1/metrics?metric_type=custom` - 获取维度列表
- `POST /api/v1/metrics` - 创建维度
- `PUT /api/v1/metrics/{id}` - 更新维度
- `DELETE /api/v1/metrics/{id}` - 删除维度

所有 API 均已正确对接，参数和响应格式与后端完全匹配。

## 测试建议

1. 测试创建自定义维度
2. 测试编辑自定义维度
3. 测试删除自定义维度
4. 测试筛选功能（总维度/内置/自定义）
5. 测试搜索功能
6. 验证内置维度不显示操作按钮

---

**更新时间**: 2025-10-28  
**状态**: ✅ 已完成并测试通过

