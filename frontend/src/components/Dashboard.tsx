import { useSystemStatus, useMismatchedDevices, usePortsWithErrors, refreshData } from '../hooks/useApi';
import { DeviceTable } from './DeviceTable';
import { ErrorsTable } from './ErrorsTable';

interface StatCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  type?: 'default' | 'success' | 'warning' | 'error';
}

function StatCard({ title, value, subtitle, type = 'default' }: StatCardProps) {
  const colors = {
    default: 'bg-white',
    success: 'bg-green-50 border-green-200',
    warning: 'bg-yellow-50 border-yellow-200',
    error: 'bg-red-50 border-red-200',
  };

  const textColors = {
    default: 'text-gray-900',
    success: 'text-green-700',
    warning: 'text-yellow-700',
    error: 'text-red-700',
  };

  return (
    <div className={`rounded-lg shadow p-6 border ${colors[type]}`}>
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>
      <p className={`text-3xl font-bold mt-2 ${textColors[type]}`}>{value}</p>
      {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
}

export function Dashboard() {
  const { status, loading: statusLoading, error: statusError } = useSystemStatus();
  const { devices: mismatchedDevices, loading: devicesLoading } = useMismatchedDevices();
  const { ports: portsWithErrors, loading: portsLoading } = usePortsWithErrors();

  const handleRefresh = async () => {
    try {
      await refreshData();
      window.location.reload();
    } catch (err) {
      console.error('Failed to refresh data:', err);
    }
  };

  const formatLastUpdate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleTimeString();
  };

  if (statusLoading || devicesLoading || portsLoading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (statusError) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-red-500">Error: {statusError}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">NLNetworkStats</h1>
              <p className="text-sm text-gray-500">
                Last update: {formatLastUpdate(status?.last_update || null)}
              </p>
            </div>
            <button
              onClick={handleRefresh}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Refresh Now
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Devices"
            value={status?.total_devices || 0}
            subtitle={`${status?.online_devices || 0} online`}
          />
          <StatCard
            title="Speed Mismatches"
            value={status?.mismatched_speeds || 0}
            type={status?.mismatched_speeds ? 'error' : 'success'}
          />
          <StatCard
            title="Ports with Errors"
            value={status?.ports_with_errors || 0}
            type={status?.ports_with_errors ? 'warning' : 'success'}
          />
          <StatCard
            title="Switches Connected"
            value={`${status?.switches_connected || 0}/${status?.switches_total || 0}`}
            type={
              status?.switches_connected === status?.switches_total
                ? 'success'
                : 'warning'
            }
          />
        </div>

        {/* Speed Mismatches Table */}
        <div className="mb-8">
          <DeviceTable
            devices={mismatchedDevices}
            title="Speed Mismatches"
            showAll={true}
          />
        </div>

        {/* Port Errors Table */}
        <div>
          <ErrorsTable ports={portsWithErrors} title="Ports with Errors" />
        </div>
      </main>
    </div>
  );
}
