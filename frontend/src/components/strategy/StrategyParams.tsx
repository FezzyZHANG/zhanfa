import type { ParamDef } from '@/types';

interface StrategyParamsProps {
  params: Record<string, ParamDef>;
}

export function StrategyParams({ params }: StrategyParamsProps) {
  const entries = Object.entries(params);
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">无参数配置</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left py-2 pr-4 font-medium text-muted-foreground">参数名</th>
            <th className="text-left py-2 pr-4 font-medium text-muted-foreground">类型</th>
            <th className="text-left py-2 pr-4 font-medium text-muted-foreground">默认值</th>
            <th className="text-left py-2 font-medium text-muted-foreground">说明</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([name, def]) => (
            <tr key={name} className="border-b border-border last:border-0">
              <td className="py-2.5 pr-4 font-mono text-xs">{name}</td>
              <td className="py-2.5 pr-4">
                <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{def.type}</code>
              </td>
              <td className="py-2.5 pr-4 font-mono text-xs">{String(def.default)}</td>
              <td className="py-2.5 text-muted-foreground">{def.description || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
