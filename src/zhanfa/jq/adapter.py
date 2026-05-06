"""JoinQuant 适配层 - 本地策略 → JQ API 代码生成

用于将本地验证通过的策略翻译为聚宽平台的 initialize() + handle_data() 骨架，
方便在 JoinQuant 云端做仿真/实盘验证。
"""

from __future__ import annotations

import pandas as pd

from zhanfa.strategies.base import BaseStrategy


def to_jq_template(strategy: BaseStrategy, signals: pd.Series | None = None) -> str:
    """将策略转为 JoinQuant 代码骨架。

    生成的代码需要在 JoinQuant 平台手动补充具体的入场/出场判断逻辑。
    策略参数已内联为局部变量，可直接在条件判断中使用。

    Args:
        strategy: 策略实例。
        signals: 可选，策略已生成的信号序列，用于统计（非必须）。
    """
    params = _extract_params(strategy)
    param_decls = _format_param_decls(params)
    buy_condition, sell_condition = _format_signal_conditions(params, signals)

    lines = [
        "# 自动生成骨架 - zhanfa → JoinQuant",
        f"# 策略: {strategy.__class__.__name__}",
        f"# 本地策略参数: {params}",
        "",
        "def initialize(context):",
        "    g.stock = '000300.XSHG'  # 替换为实际标的",
        f"    g.params = {params}",
        "    set_benchmark('000300.XSHG')",
        "    set_option('use_real_price', True)",
        "    log.info('策略初始化完成')",
        "",
        "def handle_data(context, data):",
        "    stock = g.stock",
        "",
        *[f"    {d}" for d in param_decls],
        "",
        "    # 获取历史数据",
        "    df = attribute_history(stock, 120, '1d', ['open', 'high', 'low', 'close', 'volume'])",
        "    if df is None or len(df) < 60:",
        "        return",
        "",
        "    close = df['close']",
        "    high = df['high']",
        "    low = df['low']",
        "",
        "    # === 信号计算（根据策略逻辑填充） ===",
        f"    buy_signal = {buy_condition}",
        f"    sell_signal = {sell_condition}",
        "",
        "    # === 交易执行 ===",
        "    cash = context.portfolio.available_cash",
        "    position = context.portfolio.positions[stock]",
        "",
        "    if buy_signal and position.total_amount == 0:",
        "        order_value(stock, cash * 0.8)",
        "    elif sell_signal and position.total_amount > 0:",
        "        order_target(stock, 0)",
        "",
        "",
        f"# 本地策略名称: {strategy.name}",
        f"# 本地策略类: {strategy.__class__.__name__}",
        f"# 参数: {params}",
    ]
    if signals is not None:
        lines.append(f"# 信号统计: 买入 {signals.astype(bool).sum()} 次, 共 {len(signals)} 根K线")
    return "\n".join(lines)


def _extract_params(strategy: BaseStrategy) -> dict:
    """提取策略构造参数（排除私有属性和 name）"""
    params = {}
    for k, v in strategy.__dict__.items():
        if not k.startswith("_") and k != "name":
            params[k] = v
    return params


def _format_param_decls(params: dict) -> list[str]:
    """将策略参数展开为局部变量声明"""
    lines = []
    lines.append("# 策略参数")
    for k, v in params.items():
        if isinstance(v, (int, float, bool)):
            lines.append(f"{k} = g.params['{k}']  # = {v}")
        else:
            lines.append(f"{k} = g.params['{k}']")
    return lines


def _format_signal_conditions(params: dict, signals: pd.Series | None) -> tuple[str, str]:
    """生成买卖条件的占位符表达式。

    根据策略参数给出合理的条件提示，例如：
    - MACD 类参数（fast/slow/signal）→ 提示 DIF 上穿 DEA
    - MA 类参数 → 提示价格上穿均线
    - RSI 参数 → 提示超买超卖
    """
    buy = "False  # TODO: 填入买入条件"
    sell = "False  # TODO: 填入卖出条件"

    if not params:
        return buy, sell

    # 根据参数名推断策略类型，给出更具体的提示
    has_macd = all(k in params for k in ("fast", "slow"))

    if has_macd:
        fast = params.get("fast", 12)
        slow = params.get("slow", 26)
        sig = params.get("signal", 9)
        buy = f"False  # e.g., MACD DIF > DEA (fast={fast}, slow={slow}, signal={sig})"
        sell = f"False  # e.g., MACD DIF < DEA (fast={fast}, slow={slow}, signal={sig})"
    elif "period" in params and ("overbought" in str(params) or "oversold" in str(params)):
        period = params.get("period", 14)
        buy = f"False  # e.g., RSI 上穿超卖线 (period={period})"
        sell = f"False  # e.g., RSI 下穿超买线 (period={period})"
    elif "period" in params:
        period = params["period"]
        buy = f"False  # e.g., close > MA(close, {period})"
        sell = f"False  # e.g., close < MA(close, {period})"

    return buy, sell
