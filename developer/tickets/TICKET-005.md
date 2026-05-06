# TICKET-005: 财报分析模块

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** 001, 003
**预计工时:** 3d

## 需求描述

在个股详情页提供财报数据的可视化分析，覆盖利润表、资产负债表、现金流量表核心指标，以及关键估值指标的趋势变化。

## 功能清单

### 核心指标卡片

展示最新报告期关键数字：

| 指标       | 说明       |
| ---------- | ---------- |
| 净利润     | 近 4 季度趋势 |
| 营业收入   | 同比/环比增长率 |
| EPS        | 每股收益   |
| ROE        | 净资产收益率 |
| 资产负债率 | 杠杆水平   |
| 股息率     | 分红回报   |

### 趋势图表

- [x] 营收 & 净利润 双轴柱线图 (最近 5 年/10 期)
- [x] ROE 趋势折线图 (杜邦分析拆分可选)
- [x] 毛利率 / 净利率 对比折线图
- [x] PE / PB 历史分位图（当前值在历史区间的排位）
- [x] 资产负债率 & 流动比率 趋势

### 财报对比

- [x] 同行业公司关键指标对比表（从 stocks 表筛选同 industry）
- [x] 雷达图：公司在行业内的 ROE/毛利率/负债率/营收增速 排位

### 数据表格

- [x] 完整财报数据表格（支持按报告期筛选和排序）
- [x] CSV/Excel 导出

## 技术方案

```typescript
// 财报图表混用 ECharts
import ReactECharts from 'echarts-for-react';

interface FinancialPanelProps {
  code: string;
  years?: number;  // 显示最近 N 年
}
```

## 组件拆分

```
components/financial/
├── FinancialPanel.tsx      # 主容器，管理 years 选择
├── MetricCards.tsx         # 顶部指标卡片行
├── RevenueProfitChart.tsx  # 营收&净利润双轴图
├── ROEChart.tsx            # ROE 趋势
├── MarginChart.tsx         # 毛利率/净利率
├── ValuationChart.tsx      # PE/PB 历史分位
├── IndustryRadar.tsx       # 行业对比雷达图
├── FinancialTable.tsx      # 完整数据表格
└── useFinancialData.ts     # 数据获取 hook
```

## 验收标准

- [x] 指标卡片正确显示最新一期数据
- [x] 各趋势图正确渲染至少 5 年数据
- [x] PE/PB 分位图计算正确（当前值 vs 历史区间）
- [x] 行业对比雷达图选取同行业公司正确
- [x] 表格排序/筛选正常
- [x] 导出功能正常（CSV 格式）

## 备注

- 财报数据来自 `/api/stocks/{code}/financial`，后端缓存自 akshare
- 历史分位计算：如果数据不足 5 年则显示可用的全部区间
- 行业分类使用申万一级行业（akshare 返回的字段）
