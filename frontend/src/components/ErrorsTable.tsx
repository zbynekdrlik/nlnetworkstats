import { PortErrors } from '../types';

interface ErrorsTableProps {
  ports: PortErrors[];
  title: string;
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
}

export function ErrorsTable({ ports, title }: ErrorsTableProps) {
  const portsWithIssues = ports.filter((p) => p.has_issues);

  if (portsWithIssues.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">{title}</h2>
        <p className="text-green-600 text-center py-4">
          No ports with errors detected
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
                Switch
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Port
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Speed
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                RX Drop
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                TX Drop
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                RX Err
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                TX Err
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                FCS Err
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {portsWithIssues.map((port) => (
              <tr key={`${port.switch_name}-${port.port_name}`} className="bg-yellow-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {port.switch_name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {port.port_name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {port.speed || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  <span className={port.rx_dropped > 0 ? 'text-red-600 font-semibold' : 'text-gray-500'}>
                    {formatNumber(port.rx_dropped)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  <span className={port.tx_dropped > 0 ? 'text-red-600 font-semibold' : 'text-gray-500'}>
                    {formatNumber(port.tx_dropped)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  <span className={port.rx_errors > 0 ? 'text-red-600 font-semibold' : 'text-gray-500'}>
                    {formatNumber(port.rx_errors)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  <span className={port.tx_errors > 0 ? 'text-red-600 font-semibold' : 'text-gray-500'}>
                    {formatNumber(port.tx_errors)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  <span
                    className={
                      port.rx_fcs_errors + port.tx_fcs_errors > 0
                        ? 'text-red-600 font-semibold'
                        : 'text-gray-500'
                    }
                  >
                    {formatNumber(port.rx_fcs_errors + port.tx_fcs_errors)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
