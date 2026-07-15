#!/usr/bin/env python3
"""Joystick mux-input contract: idle releases, deliberate axes take control."""

from __future__ import annotations

import argparse
import os
import subprocess
import time

os.environ.setdefault("ROS_DOMAIN_ID", "185")

import rclpy  # noqa: E402
from mavros_msgs.msg import OverrideRCIn  # noqa: E402
from rclpy.node import Node  # noqa: E402
from sensor_msgs.msg import Joy  # noqa: E402


class Probe(Node):
    def __init__(self) -> None:
        super().__init__("joy2mavros_mux_input_probe")
        self.pub = self.create_publisher(Joy, "/joy", 10)
        self.last: OverrideRCIn | None = None
        self.create_subscription(OverrideRCIn, "/test/joy/rc", self._on_rc, 10)

    def _on_rc(self, message: OverrideRCIn) -> None:
        self.last = message

    def publish(self, forward: float) -> None:
        message = Joy()
        message.axes = [0.0] * 8
        message.buttons = [0] * 12
        message.axes[1] = forward
        self.pub.publish(message)


def wait_for(probe: Probe, forward: float, predicate, timeout_s: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        probe.publish(forward)
        rclpy.spin_once(probe, timeout_sec=0.03)
        if predicate():
            return
    raise RuntimeError("joy2mavros mux-input condition timed out")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True)
    args = parser.parse_args()
    process = subprocess.Popen(
        [
            args.executable,
            "--ros-args",
            "-p", "rc_output_topic:=/test/joy/rc",
            "-p", "release_when_idle:=true",
            "-p", "axis_deadband:=0.05",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=os.environ.copy(),
    )
    rclpy.init()
    probe = Probe()
    try:
        # joy2mavros intentionally consumes the first Joy sample as its edge baseline.
        wait_for(
            probe,
            0.0,
            lambda: probe.last is not None
            and all(value == OverrideRCIn.CHAN_RELEASE for value in probe.last.channels),
        )
        wait_for(
            probe,
            0.4,
            lambda: probe.last is not None and probe.last.channels[4] > 1500,
        )
        wait_for(
            probe,
            0.0,
            lambda: probe.last is not None
            and all(value == OverrideRCIn.CHAN_RELEASE for value in probe.last.channels),
        )
        print("joy2mavros_mux_input=PASS idle=RELEASE motion=ACTIVE")
        return 0
    finally:
        probe.destroy_node()
        rclpy.shutdown()
        process.terminate()
        try:
            output, _ = process.communicate(timeout=3.0)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate(timeout=1.0)
        if process.returncode not in (0, -15):
            raise RuntimeError(f"joy2mavros exited {process.returncode}:\n{output}")


if __name__ == "__main__":
    raise SystemExit(main())
