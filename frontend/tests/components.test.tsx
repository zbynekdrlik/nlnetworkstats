import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../src/components/StatusBadge';
import { DeviceTable } from '../src/components/DeviceTable';
import { ErrorsTable } from '../src/components/ErrorsTable';
import { DeviceStatus, PortErrors } from '../src/types';

describe('StatusBadge', () => {
  it('renders with ok status', () => {
    render(<StatusBadge status="ok" text="OK" />);
    expect(screen.getByText('OK')).toBeInTheDocument();
  });

  it('renders with error status', () => {
    render(<StatusBadge status="error" text="Error" />);
    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('renders with warning status', () => {
    render(<StatusBadge status="warning" text="Warning" />);
    expect(screen.getByText('Warning')).toBeInTheDocument();
  });

  it('renders with offline status', () => {
    render(<StatusBadge status="offline" text="Offline" />);
    expect(screen.getByText('Offline')).toBeInTheDocument();
  });
});

describe('DeviceTable', () => {
  const mockDevices: DeviceStatus[] = [
    {
      name: 'Server-01',
      ip: '192.168.1.100',
      mac: 'AA:BB:CC:DD:EE:01',
      expected_speed: '1Gbps',
      actual_speed: '100Mbps',
      switch_name: 'switch-1',
      port_name: 'ether1',
      speed_match: false,
      online: true,
      last_seen: '2024-01-01T00:00:00',
    },
    {
      name: 'Server-02',
      ip: '192.168.1.101',
      mac: 'AA:BB:CC:DD:EE:02',
      expected_speed: '1Gbps',
      actual_speed: '1Gbps',
      switch_name: 'switch-1',
      port_name: 'ether2',
      speed_match: true,
      online: true,
      last_seen: '2024-01-01T00:00:00',
    },
  ];

  it('renders table with devices', () => {
    render(<DeviceTable devices={mockDevices} title="Test Devices" showAll />);
    expect(screen.getByText('Test Devices')).toBeInTheDocument();
    expect(screen.getByText('Server-01')).toBeInTheDocument();
    expect(screen.getByText('Server-02')).toBeInTheDocument();
  });

  it('shows only mismatched devices when showAll is false', () => {
    render(<DeviceTable devices={mockDevices} title="Mismatched" />);
    expect(screen.getByText('Server-01')).toBeInTheDocument();
    expect(screen.queryByText('Server-02')).not.toBeInTheDocument();
  });

  it('shows success message when no mismatched devices', () => {
    const okDevices: DeviceStatus[] = [
      {
        ...mockDevices[1],
      },
    ];
    render(<DeviceTable devices={okDevices} title="Mismatched" />);
    expect(screen.getByText('All devices are running at expected speeds')).toBeInTheDocument();
  });
});

describe('ErrorsTable', () => {
  const mockPorts: PortErrors[] = [
    {
      switch_name: 'switch-1',
      port_name: 'ether1',
      link_status: 'up',
      speed: '1Gbps',
      rx_bytes: 1000000,
      tx_bytes: 2000000,
      rx_dropped: 100,
      tx_dropped: 50,
      rx_errors: 10,
      tx_errors: 5,
      rx_fcs_errors: 0,
      tx_fcs_errors: 0,
      has_issues: true,
    },
    {
      switch_name: 'switch-1',
      port_name: 'ether2',
      link_status: 'up',
      speed: '1Gbps',
      rx_bytes: 500000,
      tx_bytes: 600000,
      rx_dropped: 0,
      tx_dropped: 0,
      rx_errors: 0,
      tx_errors: 0,
      rx_fcs_errors: 0,
      tx_fcs_errors: 0,
      has_issues: false,
    },
  ];

  it('renders table with ports that have issues', () => {
    render(<ErrorsTable ports={mockPorts} title="Port Errors" />);
    expect(screen.getByText('Port Errors')).toBeInTheDocument();
    expect(screen.getByText('ether1')).toBeInTheDocument();
  });

  it('does not show ports without issues', () => {
    render(<ErrorsTable ports={mockPorts} title="Port Errors" />);
    expect(screen.queryByText('ether2')).not.toBeInTheDocument();
  });

  it('shows success message when no ports have errors', () => {
    const okPorts: PortErrors[] = [mockPorts[1]];
    render(<ErrorsTable ports={okPorts} title="Port Errors" />);
    expect(screen.getByText('No ports with errors detected')).toBeInTheDocument();
  });
});
