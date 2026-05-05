"""策略基类 - 所有策略必须继承并实现 generate_signals"""

from abc import ABC, abstractmethod

import pandas as pd


class BaseStrategy(ABC):
    """策略基类。

    子类需实现 `generate_signals`，返回 pd.Series：
    - bool 类型：True = 持有/买入, False = 空仓/卖出
    - float 类型：仓位权重 [0, 1]

    产出结果可直接喂入 vectorbt 的 vbt.Portfolio.from_signals()。
    """

    name: str = "base"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """从历史行情生成交易信号。

        Args:
            data: 包含 open/high/low/close/volume 列的 DataFrame，index 为日期。

        Returns:
            信号序列，index 对齐 data.index。
        """
        ...

    def fit(self, data: pd.DataFrame) -> None:
        """[预留接口] 用历史数据训练/调参。

        机器学习类策略覆写此方法进行模型训练或参数优化。
        当前项目中尚无 ML 策略实现，接口保留供未来扩展使用。
        """
        pass

    def position_weights(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """多标的仓位分配（组合策略可覆写）。

        Args:
            data: {code: DataFrame} 各标的的行情数据。

        Returns:
            DataFrame，index=日期, columns=code, values=weight [0, 1]。
        """
        signals = {}
        for code, df in data.items():
            signals[code] = self.generate_signals(df)
        return pd.DataFrame(signals).sort_index()
