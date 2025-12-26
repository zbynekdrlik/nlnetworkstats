export interface DeviceStatus {
  name: string;
  ip: string;
  mac: string | null;
  expected_speed: string;
  actual_speed: string | null;
  switch_name: string | null;
  port_name: string | null;
  speed_match: boolean;
  online: boolean;
  last_seen: string | null;
}

export interface PortErrors {
  switch_name: string;
  port_name: string;
  link_status: string;
  speed: string | null;
  rx_bytes: number;
  tx_bytes: number;
  rx_dropped: number;
  tx_dropped: number;
  rx_errors: number;
  tx_errors: number;
  rx_fcs_errors: number;
  tx_fcs_errors: number;
  has_issues: boolean;
}

export interface SwitchStatus {
  name: string;
  host: string;
  connected: boolean;
  error: string | null;
  last_check: string | null;
}

export interface SystemStatus {
  total_devices: number;
  online_devices: number;
  mismatched_speeds: number;
  ports_with_errors: number;
  switches_connected: number;
  switches_total: number;
  last_update: string | null;
}
