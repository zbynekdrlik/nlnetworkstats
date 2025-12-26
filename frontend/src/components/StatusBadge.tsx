interface StatusBadgeProps {
  status: 'ok' | 'warning' | 'error' | 'offline';
  text: string;
}

export function StatusBadge({ status, text }: StatusBadgeProps) {
  const colors = {
    ok: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    error: 'bg-red-100 text-red-800',
    offline: 'bg-gray-100 text-gray-800',
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status]}`}>
      {text}
    </span>
  );
}
