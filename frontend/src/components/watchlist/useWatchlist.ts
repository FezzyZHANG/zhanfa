import { useState, useCallback } from 'react';
import type { Watchlist } from '@/types';

export type ViewMode = 'table' | 'card';

export function useWatchlist() {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  // Dialog state
  const [groupDialog, setGroupDialog] = useState<{ open: boolean; mode: 'create' | 'rename'; wl?: Watchlist }>({ open: false, mode: 'create' });
  const [deleteTarget, setDeleteTarget] = useState<Watchlist | null>(null);
  const [addStockOpen, setAddStockOpen] = useState(false);
  const [notesEdit, setNotesEdit] = useState<{ code: string; notes: string | null } | null>(null);
  const [batchDeleteCodes, setBatchDeleteCodes] = useState<string[] | null>(null);

  const selectWatchlist = useCallback((id: number) => {
    setSelectedId(id);
  }, []);

  const openCreate = useCallback(() => setGroupDialog({ open: true, mode: 'create' }), []);
  const openRename = useCallback((wl: Watchlist) => setGroupDialog({ open: true, mode: 'rename', wl }), []);
  const closeGroupDialog = useCallback(() => setGroupDialog({ open: false, mode: 'create' }), []);

  const confirmDelete = useCallback((wl: Watchlist) => setDeleteTarget(wl), []);
  const closeDelete = useCallback(() => setDeleteTarget(null), []);

  const openAddStock = useCallback(() => setAddStockOpen(true), []);
  const closeAddStock = useCallback(() => setAddStockOpen(false), []);

  const openNotesEdit = useCallback((code: string, notes: string | null) => setNotesEdit({ code, notes }), []);
  const closeNotesEdit = useCallback(() => setNotesEdit(null), []);

  const confirmBatchDelete = useCallback((codes: string[]) => setBatchDeleteCodes(codes), []);
  const closeBatchDelete = useCallback(() => setBatchDeleteCodes(null), []);

  return {
    selectedId,
    selectWatchlist,
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
    setSelectedId,
  };
}
