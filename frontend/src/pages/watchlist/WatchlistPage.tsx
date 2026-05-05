import { useEffect } from 'react';
import { WatchlistSidebar } from '@/components/watchlist/WatchlistSidebar';
import { WatchlistTable } from '@/components/watchlist/WatchlistTable';
import { WatchlistCards } from '@/components/watchlist/WatchlistCards';
import { AddStockDialog } from '@/components/watchlist/AddStockDialog';
import { GroupDialog } from '@/components/watchlist/GroupDialog';
import { useWatchlist } from '@/components/watchlist/useWatchlist';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { getExportCsvUrl } from '@/api/client';
import {
  useWatchlists,
  useWatchlistQuotes,
  useCreateWatchlist,
  useRenameWatchlist,
  useDeleteWatchlist,
  useAddToWatchlist,
  useRemoveFromWatchlist,
  useUpdateItemNotes,
  useBatchAddItems,
  useBatchDeleteItems,
  useRefreshWatchlistData,
} from '@/hooks/useWatchlists';

export function WatchlistPage() {
  const { data: watchlists = [], isLoading } = useWatchlists();
  const {
    selectedId,
    selectWatchlist,
    setSelectedId,
    viewMode,
    setViewMode,
    groupDialog,
    openCreate,
    openRename,
    closeGroupDialog,
    deleteTarget,
    confirmDelete,
    closeDelete,
    addStockOpen,
    openAddStock,
    closeAddStock,
    notesEdit,
    openNotesEdit,
    closeNotesEdit,
    batchDeleteCodes,
    confirmBatchDelete,
    closeBatchDelete,
  } = useWatchlist();

  const { data: quotes, isLoading: quotesLoading } = useWatchlistQuotes(selectedId);
  const createMut = useCreateWatchlist();
  const renameMut = useRenameWatchlist();
  const deleteMut = useDeleteWatchlist();
  const addMut = useAddToWatchlist();
  const removeMut = useRemoveFromWatchlist();
  const updateNotesMut = useUpdateItemNotes();
  const batchAddMut = useBatchAddItems();
  const batchDeleteMut = useBatchDeleteItems();
  const refreshMut = useRefreshWatchlistData();

  // Auto-select first watchlist
  useEffect(() => {
    if (!selectedId && watchlists.length > 0) {
      setSelectedId(watchlists[0].id);
    }
  }, [selectedId, watchlists, setSelectedId]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-[400px] rounded-xl" />
      </div>
    );
  }

  const handleCreate = (name: string) => {
    createMut.mutate(name);
  };

  const handleRename = (name: string) => {
    if (groupDialog.wl) {
      renameMut.mutate({ id: groupDialog.wl.id, name });
    }
  };

  const handleDelete = () => {
    if (deleteTarget) {
      deleteMut.mutate(deleteTarget.id, {
        onSuccess: () => {
          if (selectedId === deleteTarget.id) {
            setSelectedId(null);
          }
        },
      });
      closeDelete();
    }
  };

  const handleAddStocks = (codes: string[]) => {
    if (!selectedId) return;
    if (codes.length === 1) {
      addMut.mutate({ wlId: selectedId, code: codes[0] });
    } else {
      batchAddMut.mutate({ wlId: selectedId, codes });
    }
  };

  const handleRemove = (code: string) => {
    if (!selectedId) return;
    removeMut.mutate({ wlId: selectedId, code });
  };

  const handleBatchRemove = (codes: string[]) => {
    confirmBatchDelete(codes);
  };

  const handleConfirmBatchDelete = () => {
    if (!selectedId || !batchDeleteCodes) return;
    batchDeleteMut.mutate({ wlId: selectedId, codes: batchDeleteCodes });
    closeBatchDelete();
  };

  const handleEditNotes = (code: string, notes: string | null) => {
    openNotesEdit(code, notes);
  };

  const handleSaveNotes = (notes: string | null) => {
    if (!selectedId || !notesEdit) return;
    updateNotesMut.mutate({ wlId: selectedId, code: notesEdit.code, notes });
    closeNotesEdit();
  };

  const handleRefreshGroup = () => {
    if (!selectedId || !quotes?.items) return;
    const codes = quotes.items.map((item) => item.code);
    refreshMut.mutate(codes);
  };

  const selectedWatchlist = watchlists.find((w) => w.id === selectedId);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold tracking-tight">自选股看板</h1>
        {selectedId && (
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setViewMode(viewMode === 'table' ? 'card' : 'table')}>
              {viewMode === 'table' ? '卡片视图' : '表格视图'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefreshGroup}
              disabled={refreshMut.isPending}
            >
              {refreshMut.isPending ? '刷新中...' : '刷新数据'}
            </Button>
            <Button variant="outline" size="sm" onClick={openAddStock}>
              + 添加股票
            </Button>
            <a href={getExportCsvUrl(selectedId)} download>
              <Button variant="ghost" size="sm">导出 CSV</Button>
            </a>
          </div>
        )}
      </div>

      <div className="flex gap-6">
        <WatchlistSidebar
          watchlists={watchlists}
          selectedId={selectedId}
          onSelect={selectWatchlist}
          onCreate={openCreate}
          onRename={openRename}
          onDelete={confirmDelete}
        />

        <div className="flex-1 min-w-0">
          {!selectedWatchlist ? (
            <p className="text-center text-muted-foreground py-12">请选择一个分组</p>
          ) : quotesLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 rounded-lg" />
              ))}
            </div>
          ) : viewMode === 'table' ? (
            <WatchlistTable
              quotes={quotes?.items || []}
              onRemove={handleRemove}
              onBatchRemove={handleBatchRemove}
              onEditNotes={handleEditNotes}
            />
          ) : (
            <WatchlistCards
              quotes={quotes?.items || []}
              onRemove={handleRemove}
            />
          )}
        </div>
      </div>

      {/* Group create/rename dialog */}
      <GroupDialog
        open={groupDialog.open}
        title={groupDialog.mode === 'create' ? '新建分组' : '重命名分组'}
        initialValue={groupDialog.wl?.name}
        onClose={closeGroupDialog}
        onConfirm={groupDialog.mode === 'create' ? handleCreate : handleRename}
      />

      {/* Delete confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={closeDelete}>
          <div
            className="bg-card rounded-xl border border-border shadow-xl w-full max-w-sm p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold mb-2">确认删除</h3>
            <p className="text-muted-foreground mb-4">
              确定删除分组「{deleteTarget.name}」？分组内股票将被移除，但不会从系统中删除。
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={closeDelete}>取消</Button>
              <Button variant="destructive" onClick={handleDelete}>删除</Button>
            </div>
          </div>
        </div>
      )}

      {/* Batch delete confirmation */}
      {batchDeleteCodes && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={closeBatchDelete}>
          <div
            className="bg-card rounded-xl border border-border shadow-xl w-full max-w-sm p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold mb-2">确认批量移除</h3>
            <p className="text-muted-foreground mb-4">
              确定移除 {batchDeleteCodes.length} 只股票？仅从当前分组移除，不会从系统中删除。
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={closeBatchDelete}>取消</Button>
              <Button variant="destructive" onClick={handleConfirmBatchDelete} disabled={batchDeleteMut.isPending}>
                {batchDeleteMut.isPending ? '删除中...' : '删除'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Add stock dialog */}
      <AddStockDialog
        open={addStockOpen}
        onClose={closeAddStock}
        onAdd={handleAddStocks}
        wlId={selectedId}
      />

      {/* Edit notes inline dialog */}
      {notesEdit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={closeNotesEdit}>
          <div
            className="bg-card rounded-xl border border-border shadow-xl w-full max-w-sm p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold mb-4">编辑备注 - {notesEdit.code}</h3>
            <input
              autoFocus
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary mb-4"
              placeholder="添加备注..."
              defaultValue={notesEdit.notes || ''}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveNotes((e.target as HTMLInputElement).value || null);
                if (e.key === 'Escape') closeNotesEdit();
              }}
              id="notes-input"
            />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={closeNotesEdit}>取消</Button>
              <Button onClick={() => {
                const input = document.getElementById('notes-input') as HTMLInputElement;
                handleSaveNotes(input?.value || null);
              }}>
                保存
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
