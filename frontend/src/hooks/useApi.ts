import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { DeviceStatus, PortErrors, SwitchStatus, SystemStatus } from '../types';

const API_BASE = '/api';

export function useSystemStatus(refreshInterval: number = 10000) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await axios.get<SystemStatus>(`${API_BASE}/status`);
      setStatus(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch system status');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchStatus, refreshInterval]);

  return { status, loading, error, refresh: fetchStatus };
}

export function useDevices(refreshInterval: number = 10000) {
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDevices = useCallback(async () => {
    try {
      const response = await axios.get<DeviceStatus[]>(`${API_BASE}/devices`);
      setDevices(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch devices');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchDevices, refreshInterval]);

  return { devices, loading, error, refresh: fetchDevices };
}

export function useMismatchedDevices(refreshInterval: number = 10000) {
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDevices = useCallback(async () => {
    try {
      const response = await axios.get<DeviceStatus[]>(`${API_BASE}/devices/mismatched`);
      setDevices(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch mismatched devices');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchDevices, refreshInterval]);

  return { devices, loading, error, refresh: fetchDevices };
}

export function useMatchedDevices(refreshInterval: number = 10000) {
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDevices = useCallback(async () => {
    try {
      const response = await axios.get<DeviceStatus[]>(`${API_BASE}/devices/matched`);
      setDevices(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch matched devices');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchDevices, refreshInterval]);

  return { devices, loading, error, refresh: fetchDevices };
}

export function useOfflineDevices(refreshInterval: number = 10000) {
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDevices = useCallback(async () => {
    try {
      const response = await axios.get<DeviceStatus[]>(`${API_BASE}/devices/offline`);
      setDevices(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch offline devices');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchDevices, refreshInterval]);

  return { devices, loading, error, refresh: fetchDevices };
}

export function usePortsWithErrors(refreshInterval: number = 10000) {
  const [ports, setPorts] = useState<PortErrors[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPorts = useCallback(async () => {
    try {
      const response = await axios.get<PortErrors[]>(`${API_BASE}/ports/errors`);
      setPorts(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch ports with errors');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPorts();
    const interval = setInterval(fetchPorts, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchPorts, refreshInterval]);

  return { ports, loading, error, refresh: fetchPorts };
}

export function useHealthyPorts(refreshInterval: number = 10000) {
  const [ports, setPorts] = useState<PortErrors[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPorts = useCallback(async () => {
    try {
      const response = await axios.get<PortErrors[]>(`${API_BASE}/ports/healthy`);
      setPorts(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch healthy ports');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPorts();
    const interval = setInterval(fetchPorts, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchPorts, refreshInterval]);

  return { ports, loading, error, refresh: fetchPorts };
}

export function useSwitches(refreshInterval: number = 10000) {
  const [switches, setSwitches] = useState<SwitchStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSwitches = useCallback(async () => {
    try {
      const response = await axios.get<SwitchStatus[]>(`${API_BASE}/switches`);
      setSwitches(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch switches');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSwitches();
    const interval = setInterval(fetchSwitches, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchSwitches, refreshInterval]);

  return { switches, loading, error, refresh: fetchSwitches };
}

export async function refreshData(): Promise<void> {
  await axios.post(`${API_BASE}/refresh`);
}
