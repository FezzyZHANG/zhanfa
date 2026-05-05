"""导出策略为 JoinQuant 代码"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zhanfa.strategies.trend.sma_cross import SMACross
from zhanfa.strategies.trend.turtle import Turtle
from zhanfa.jq.adapter import to_jq_template


def main():
    strategies = {
        "sma_cross": SMACross(),
        "turtle": Turtle(),
    }

    name = sys.argv[1] if len(sys.argv) > 1 else "sma_cross"
    s = strategies.get(name)
    if s is None:
        print(f"未知策略: {name}，可选: {list(strategies.keys())}")
        return

    code = to_jq_template(s)
    print(code)
    print(f"\n# 保存到文件: export_jq_{name}.py")
    with open(f"export_jq_{name}.py", "w", encoding="utf-8") as f:
        f.write(code)


if __name__ == "__main__":
    main()
