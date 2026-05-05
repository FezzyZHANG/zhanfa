import { useState } from 'react';
import { Button } from '@/components/ui/Button';

interface GroupDialogProps {
  open: boolean;
  title: string;
  initialValue?: string;
  onClose: () => void;
  onConfirm: (name: string) => void;
}

export function GroupDialog({ open, title, initialValue = '', onClose, onConfirm }: GroupDialogProps) {
  const [name, setName] = useState(initialValue);

  if (!open) return null;

  const handleConfirm = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    onConfirm(trimmed);
    setName('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-card rounded-xl border border-border shadow-xl w-full max-w-sm p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <input
          autoFocus
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary mb-4"
          placeholder="分组名称"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleConfirm(); }}
        />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>取消</Button>
          <Button onClick={handleConfirm} disabled={!name.trim()}>确定</Button>
        </div>
      </div>
    </div>
  );
}
