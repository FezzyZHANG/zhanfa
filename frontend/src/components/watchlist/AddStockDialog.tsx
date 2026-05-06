import { useState, useEffect } from 'react';
import { useSearchStocks, useBatchAddPreview } from '@/hooks/useWatchlists';
import { Button } from '@/components/ui/Button';
import type { StockSearchResult, BatchPreviewItem } from '@/types';

interface AddStockDialogProps {
  open: boolean;
  onClose: () => void;
  onAdd: (codes: string[]) => void;
  wlId?: number | null;
}

export function AddStockDialog({ open, onClose, onAdd, wlId }: AddStockDialogProps) {
  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [pasteMode, setPasteMode] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [previewData, setPreviewData] = useState<BatchPreviewItem[] | null>(null);
  const [previewSelected, setPreviewSelected] = useState<Set<string>>(new Set());

  const previewMut = useBatchAddPreview();

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const { data: results = [], isLoading } = useSearchStocks(debounced);

  const handleClose = () => {
    setQuery('');
    setDebounced('');
    setSelected(new Set());
    setPasteMode(false);
    setPasteText('');
    setPreviewData(null);
    setPreviewSelected(new Set());
    onClose();
  };

  if (!open) return null;

  const toggle = (code: string) => {
    const next = new Set(selected);
    if (next.has(code)) next.delete(code); else next.add(code);
    setSelected(next);
  };

  const handlePastePreview = async () => {
    const codes = pasteText
      .split(/[\n,;，；\s]+/)
      .map((s) => s.trim())
      .filter((s) => /^\d{6}$/.test(s));
    if (codes.length === 0) return;

    if (wlId) {
      const result = await previewMut.mutateAsync({ wlId, codes });
      setPreviewData(result.preview);
      setPreviewSelected(new Set(codes.filter((c) => !result.preview.find((p) => p.code === c)?.in_current)));
    } else {
      // Fallback without preview API: mark all as new
      setPreviewData(codes.map((code) => ({ code, name: '', in_current: false, in_other: [] })));
      setPreviewSelected(new Set(codes));
    }
  };

  const handleConfirmPreview = () => {
    const codes = Array.from(previewSelected);
    if (codes.length > 0) onAdd(codes);
    handleClose();
  };

  const handleAdd = () => {
    if (pasteMode) {
      if (!previewData) {
        handlePastePreview();
        return;
      }
      handleConfirmPreview();
    } else {
      const codes = Array.from(selected);
      if (codes.length > 0) onAdd(codes);
      handleClose();
    }
  };

  const togglePreviewSelect = (code: string) => {
    setPreviewSelected((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code); else next.add(code);
      return next;
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={handleClose}>
      <div
        className="bg-card rounded-xl border border-border shadow-xl w-full max-w-md p-6 max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">添加股票</h3>
          <button className="text-muted-foreground hover:text-foreground" onClick={handleClose}>✕</button>
        </div>

        <div className="flex gap-2 mb-4">
          <Button
            variant={pasteMode ? 'ghost' : 'default'}
            size="sm"
            onClick={() => { setPasteMode(false); setPreviewData(null); }}
          >
            搜索
          </Button>
          <Button
            variant={pasteMode ? 'default' : 'ghost'}
            size="sm"
            onClick={() => { setPasteMode(true); setPreviewData(null); }}
          >
            批量粘贴
          </Button>
        </div>

        {pasteMode ? (
          <>
            {!previewData ? (
              <>
                <textarea
                  className="w-full h-32 rounded-md border border-border bg-background p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="粘贴股票代码，每行一个或用逗号分隔&#10;例如：&#10;600519&#10;000858,300750"
                  value={pasteText}
                  onChange={(e) => setPasteText(e.target.value)}
                />
                <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-border">
                  <Button variant="ghost" onClick={handleClose}>取消</Button>
                  <Button
                    onClick={handleAdd}
                    disabled={!pasteText.trim() || previewMut.isPending}
                  >
                    {previewMut.isPending ? '加载中...' : '预览'}
                  </Button>
                </div>
              </>
            ) : (
              <>
                <div className="flex-1 overflow-y-auto min-h-[200px]">
                  <p className="text-xs text-muted-foreground mb-2">
                    已解析 {previewData.length} 只股票，其中 {previewData.filter((p) => p.in_current).length} 只已在当前分组
                  </p>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs text-muted-foreground">
                        <th className="py-2 px-1 w-8" />
                        <th className="py-2 px-1">代码</th>
                        <th className="py-2 px-1">名称</th>
                        <th className="py-2 px-1">状态</th>
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.map((p) => (
                        <tr key={p.code} className="border-b border-border text-xs">
                          <td className="py-2 px-1">
                            <input
                              type="checkbox"
                              className="rounded"
                              checked={previewSelected.has(p.code)}
                              onChange={() => togglePreviewSelect(p.code)}
                              disabled={p.in_current}
                            />
                          </td>
                          <td className="py-2 px-1 font-mono">{p.code}</td>
                          <td className="py-2 px-1">{p.name || '--'}</td>
                          <td className="py-2 px-1">
                            <span className={p.in_current ? 'text-yellow-500' : 'text-green-500'}>
                              {p.in_current ? '已在当前分组' : p.in_other.length > 0 ? `已在: ${p.in_other.join(', ')}` : '新股票'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-border">
                  <Button variant="ghost" onClick={() => setPreviewData(null)}>返回</Button>
                  <Button
                    onClick={handleConfirmPreview}
                    disabled={previewSelected.size === 0}
                  >
                    添加所选 ({previewSelected.size})
                  </Button>
                </div>
              </>
            )}
          </>
        ) : (
          <>
            <input
              autoFocus
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary mb-4"
              placeholder="输入代码或名称搜索..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="flex-1 overflow-y-auto min-h-[200px]">
              {isLoading && <p className="text-center text-muted-foreground py-4">搜索中...</p>}
              {!isLoading && results.length === 0 && debounced && (
                <p className="text-center text-muted-foreground py-4">无匹配结果</p>
              )}
              {results.map((s: StockSearchResult) => (
                <label
                  key={s.code}
                  className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-accent cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(s.code)}
                    onChange={() => toggle(s.code)}
                    className="rounded"
                  />
                  <span className="font-mono text-xs text-muted-foreground">{s.code}</span>
                  <span className="text-sm">{s.name}</span>
                </label>
              ))}
            </div>
            <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-border">
              <Button variant="ghost" onClick={handleClose}>取消</Button>
              <Button
                onClick={handleAdd}
                disabled={selected.size === 0}
              >
                添加
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
