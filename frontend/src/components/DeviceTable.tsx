import { DeviceStatus } from '../types';
import { StatusBadge } from './StatusBadge';

interface DeviceTableProps {
  devices: DeviceStatus[];
  title: string;
  showAll?: boolean;
}

export function DeviceTable({ devices, title, showAll = false }: DeviceTableProps) {
  const filteredDevices = showAll
    ? devices
    : devices.filter((d) => d.online && !d.speed_match);

  if (filteredDevices.length === 0 && !showAll) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">{title}</h2>
        <p className="text-green-600 text-center py-4">
          All devices are running at expected speeds
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Device
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                IP Address
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Expected
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actual
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Switch
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Port
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredDevices.map((device) => (
              <tr
                key={device.ip}
                className={
                  !device.online
                    ? 'bg-gray-50'
                    : !device.speed_match
                    ? 'bg-red-50'
                    : ''
                }
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {device.name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {device.ip}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {device.expected_speed}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span
                    className={
                      device.online && !device.speed_match
                        ? 'text-red-600 font-semibold'
                        : 'text-gray-500'
                    }
                  >
                    {device.actual_speed || '-'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {device.switch_name || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {device.port_name || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {!device.online ? (
                    <StatusBadge status="offline" text="Offline" />
                  ) : device.speed_match ? (
                    <StatusBadge status="ok" text="OK" />
                  ) : (
                    <StatusBadge status="error" text="Mismatch" />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
