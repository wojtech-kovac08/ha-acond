#!/usr/bin/env python3
"""Scan the Modbus register map of an Acond heat pump.

Finds out which input registers (30001+) the unit really implements, so the
integration can be trimmed to them.

Usage:
    pip install pymodbus
    python probe_acond.py 192.168.0.11
    python probe_acond.py 192.168.0.11 --unit 1 --start 30001 --end 30079

The output tells you, address by address, whether the unit answered and with
which value. Nothing is ever written to the unit.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import sys

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException


def unit_kwarg() -> str:
    params = inspect.signature(AsyncModbusTcpClient.read_input_registers).parameters
    for name in ("device_id", "slave", "unit"):
        if name in params:
            return name
    return "slave"


async def scan(host: str, port: int, unit: int, start: int, end: int, timeout: float):
    client = AsyncModbusTcpClient(host, port=port, timeout=timeout)
    if not await client.connect():
        print(f"Cannot connect to {host}:{port}")
        return 1

    kw = unit_kwarg()
    results: dict[int, tuple[bool, int | None, str]] = {}

    try:
        for address in range(start, end + 1):
            offset = address - 30001
            value = None
            ok = False
            note = ""
            for func_name in ("read_input_registers", "read_holding_registers"):
                func = getattr(client, func_name)
                try:
                    response = await func(offset, count=1, **{kw: unit})
                except ModbusException as err:
                    note = f"{type(err).__name__}"
                    continue
                except Exception as err:  # noqa: BLE001
                    note = f"{type(err).__name__}: {err}"
                    continue
                if response is None:
                    note = "no response"
                    continue
                if response.isError():
                    note = str(response)
                    continue
                value = response.registers[0]
                ok = True
                note = "FC4" if func_name == "read_input_registers" else "FC3"
                break
            results[address] = (ok, value, note)
            print(f"  {address}: {'OK ' + str(value) if ok else 'refused'}  ({note})", flush=True)
    finally:
        client.close()

    print("\n=== summary ===")
    run_start = None
    previous = None
    for address in range(start, end + 1):
        ok = results[address][0]
        if ok and run_start is None:
            run_start = address
        if not ok and run_start is not None:
            print(f"{run_start}-{previous}: implemented")
            run_start = None
        previous = address
    if run_start is not None:
        print(f"{run_start}-{previous}: implemented")

    missing = [a for a in range(start, end + 1) if not results[a][0]]
    if missing:
        print("refused:", ", ".join(str(a) for a in missing))
    else:
        print("refused: none")

    print("\nfirst values:")
    for address in range(start, end + 1):
        ok, value, _ = results[address]
        if ok and value:
            print(f"  {address} = {value}  (/{10} = {value / 10:g})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Acond Modbus input registers")
    parser.add_argument("host", help="IP address of the heat pump")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--unit", type=int, default=1)
    parser.add_argument("--start", type=int, default=30001)
    parser.add_argument("--end", type=int, default=30079)
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()
    return asyncio.run(
        scan(args.host, args.port, args.unit, args.start, args.end, args.timeout)
    )


if __name__ == "__main__":
    sys.exit(main())
