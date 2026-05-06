"""统一配置"""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """项目全局配置"""

    # 数据
    data_dir: str = field(default_factory=lambda: os.getenv("DATA_DIR", "data"))
    risk_free_rate: float = 0.017  # 无风险利率（用于夏普等计算）

    # 数据库
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///data/zhanfa.db")
    )

    # 回测默认参数
    initial_capital: float = 100_000
    commission: float = 0.0005  # 手续费率
    slippage: float = 0.001  # 滑点

    # 自动化
    update_hour: int = 17  # 每日几点更新数据


config = Config()
