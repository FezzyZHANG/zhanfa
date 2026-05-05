import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import type { RefreshResult } from '@/types';

interface Props {
  onRefresh: (force: boolean) => Promise<RefreshResult>;
  disabled?: boolean;
}

export function RefreshButton({ onRefresh, disabled }: Props) {
  const [showDialog, setShowDialog] = useState(false);
  const [force, setForce] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RefreshResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showDialog) return;
    const handler = (e: MouseEvent) => {
      if (dialogRef.current && !dialogRef.current.contains(e.target as Node)) {
        setShowDialog(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showDialog]);

  const handleStart = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const r = await onRefresh(force);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : '刷新失败');
    } finally {
      setRunning(false);
    }
  };

  const handleClose = () => {
    if (!running) {
      setShowDialog(false);
      setResult(null);
      setError(null);
    }
  };

  const label = force ? '⚠️ 强制全量刷新' : '抓取至今';

  return (
    <div className="relative">
      <Button onClick={() => setShowDialog(true)} disabled={disabled || running}>
        {running ? '刷新中...' : label}
      </Button>

      {showDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div
            ref={dialogRef}
            className="bg-background rounded-xl border border-border shadow-lg p-6 w-full max-w-md"
          >
            <h3 className="font-semibold text-lg mb-4">数据刷新</h3>

            {running ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  正在拉取数据，请稍候...
                </div>
                <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                  <div className="bg-primary h-full animate-pulse rounded-full" style={{ width: '60%' }} />
                </div>
              </div>
            ) : result ? (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="bg-green-50 dark:bg-green-950 rounded-lg p-2">
                    <p className="text-lg font-bold text-green-600">{result.updated}</p>
                    <p className="text-xs text-muted-foreground">更新成功</p>
                  </div>
                  <div className="bg-red-50 dark:bg-red-950 rounded-lg p-2">
                    <p className="text-lg font-bold text-red-600">{result.failed}</p>
                    <p className="text-xs text-muted-foreground">失败</p>
                  </div>
                  <div className="bg-blue-50 dark:bg-blue-950 rounded-lg p-2">
                    <p className="text-lg font-bold text-blue-600">{result.new_discovered}</p>
                    <p className="text-xs text-muted-foreground">新发现</p>
                  </div>
                </div>
                {result.errors.length > 0 && (
                  <div className="max-h-32 overflow-auto text-xs text-muted-foreground space-y-1">
                    {result.errors.map((e, i) => (
                      <p key={i}>
                        {e.code}: {e.error}
                      </p>
                    ))}
                  </div>
                )}
                <Button onClick={handleClose} variant="outline" className="w-full">
                  关闭
                </Button>
              </div>
            ) : error ? (
              <div className="space-y-3">
                <p className="text-sm text-red-500">{error}</p>
                <Button onClick={handleClose} variant="outline" className="w-full">
                  关闭
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={force}
                    onChange={(e) => setForce(e.target.checked)}
                    className="rounded border-border"
                  />
                  <span className={force ? 'text-destructive font-medium' : ''}>
                    强制全量刷新（删除缓存后重新拉取）
                  </span>
                </label>
                <p className="text-xs text-muted-foreground">
                  {force
                    ? '将删除所有已缓存日线数据并从 akshare 重新拉取，耗时较长。'
                    : '仅拉取最新交易日数据，增量更新已有缓存。'}
                </p>
                <div className="flex gap-2 justify-end">
                  <Button onClick={handleClose} variant="ghost" size="sm">
                    取消
                  </Button>
                  <Button onClick={handleStart} variant={force ? 'destructive' : 'default'} size="sm">
                    {force ? '确认强制刷新' : '开始刷新'}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
