# TICKET-006: 流派/策略浏览与管理

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** 001, 003
**预计工时:** 2d

## 需求描述

提供交易流派（策略）的浏览、筛选、详情查看功能。流派信息来自数据库 strategies 表和 Python 模块的 docstring/参数定义。

## 功能清单

### 策略列表页

- [ ] 按分类 Tab 筛选：全部 / 趋势跟踪 / 动量 / 基本面 / 复合
- [ ] 策略卡片展示：名称、分类标签、一句话描述、参数预览
- [ ] 搜索：按名称/描述关键词过滤

### 策略详情页

- [ ] Markdown 渲染的策略描述（理论基础、适用场景、风控规则）
- [ ] 参数表格（参数名、类型、默认值、说明）
- [ ] 关联的历史回测结果列表（从 backtest_results 表）
- [ ] 一键跳转到回测页面（预填参数）

### 策略注册

- [ ] 后端启动时自动扫描 `zhanfa.strategies` 下所有 BaseStrategy 子类
- [ ] 自动注册到 strategies 表（如不存在）
- [ ] 从 docstring 提取描述，从 `__init__` 签名提取参数 schema

## 技术方案

```python
# 后端策略发现机制
import importlib, inspect
from zhanfa.strategies.base import BaseStrategy

def discover_strategies():
    """扫描 strategies 包，返回所有策略类"""
    for module in pkgutil.iter_modules(strategies_pkg_path):
        cls = importlib.import_module(f"zhanfa.strategies.{module.name}")
        for name, obj in inspect.getmembers(cls, inspect.isclass):
            if issubclass(obj, BaseStrategy) and obj is not BaseStrategy:
                yield name, obj
```

```typescript
// 前端类型
interface Strategy {
  id: number;
  name: string;
  category: 'trend' | 'momentum' | 'fundamental' | 'composite';
  description: string;       // Markdown
  params: Record<string, ParamDef>;
  code_ref: string;          // "zhanfa.strategies.trend.SMACross"
  backtest_count: number;    // 关联的回测次数
  created_at: string;
}
```

## 组件拆分

```
components/strategy/
├── StrategyList.tsx       # 策略列表 + 分类 Tab
├── StrategyCard.tsx       # 单个策略卡片
├── StrategyDetail.tsx     # 策略详情页
├── StrategyParams.tsx     # 参数表格
└── useStrategies.ts       # 数据获取 hook
```

## 验收标准

- [ ] 策略列表按分类正确筛选
- [ ] 搜索功能正常（中文关键词匹配）
- [ ] 策略详情 Markdown 正确渲染
- [ ] 参数表格类型/默认值/说明完整
- [ ] 策略自动发现机制正常工作（新策略类无需手动注册）
- [ ] 无关联回测时显示"暂无回测记录"提示

## 备注

- 策略描述目前存储在 docstring 和 `strategies/fundamental/央企高股息/概述.md`这类笔记中。需要统一：将笔记内容整合到策略类的 `__doc__` 中，或存入 strategies.description 字段。
- 前端 Markdown 渲染推荐 `react-markdown` + `remark-gfm`（支持表格）。
