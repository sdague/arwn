"""
Simplified MQTT broker for testing.
Based on paho-mqtt test broker but with minimal dependencies.
"""

import json
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ReceivedMessage:
    topic: str
    payload: bytes
    retain: bool
    qos: int
    timestamp: float


@dataclass
class WillMessage:
    topic: str
    payload: bytes
    retain: bool
    qos: int


class SimpleMQTTBroker:
    """A simple MQTT broker for testing purposes."""

    def __init__(self):
        """Initialize the broker."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("localhost", 0))
        self.port = self.sock.getsockname()[1]
        self.sock.settimeout(5)
        self.sock.listen(5)
        self.connections = []
        self.subscriptions = {}  # Map connection to list of topic filters
        self.messages: List[ReceivedMessage] = []
        self.retained: Dict[str, bytes] = {}
        self.wills: Dict[object, WillMessage] = {}
        self._messages_lock = threading.Lock()
        self.running = False
        self.thread = None

    def start(self):
        """Start the broker in a background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        time.sleep(0.1)  # Give broker time to start

    def _run(self):
        """Run the broker loop."""
        while self.running:
            try:
                conn, addr = self.sock.accept()
                conn.settimeout(1)
                self.connections.append(conn)
                # Handle connection in a separate thread
                handler = threading.Thread(target=self._handle_connection, args=(conn,))
                handler.daemon = True
                handler.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle_connection(self, conn):
        """Handle a single MQTT connection."""
        try:
            while self.running:
                # Read packet type and length
                data = conn.recv(2)
                if not data:
                    break

                packet_type = data[0] >> 4

                # Handle CONNECT packet (type 1)
                if packet_type == 1:
                    # Read remaining length
                    remaining = self._read_remaining_length(conn)
                    # Read the rest of the CONNECT packet
                    if remaining > 0:
                        conn.recv(remaining)
                    # Send CONNACK (successful connection)
                    connack = struct.pack("!BBBB", 0x20, 0x02, 0x00, 0x00)
                    conn.send(connack)

                # Handle PUBLISH packet (type 3)
                elif packet_type == 3:
                    # Read remaining length
                    remaining = self._read_remaining_length(conn)
                    if remaining > 0:
                        publish_data = conn.recv(remaining)
                        # Parse topic from publish packet
                        if len(publish_data) >= 2:
                            topic_len = struct.unpack("!H", publish_data[:2])[0]
                            if len(publish_data) >= 2 + topic_len:
                                topic = publish_data[2 : 2 + topic_len].decode("utf-8")
                                payload = publish_data[2 + topic_len :]
                                # Route to subscribers
                                self._route_message(topic, payload, conn)

                # Handle SUBSCRIBE packet (type 8)
                elif packet_type == 8:
                    # Read remaining length
                    remaining = self._read_remaining_length(conn)
                    payload = conn.recv(remaining) if remaining > 0 else b""
                    # Extract packet ID from payload
                    if len(payload) >= 2:
                        packet_id = struct.unpack("!H", payload[:2])[0]
                        # Parse topic filter
                        if len(payload) > 4:
                            topic_len = struct.unpack("!H", payload[2:4])[0]
                            if len(payload) >= 4 + topic_len:
                                topic_filter = payload[4 : 4 + topic_len].decode(
                                    "utf-8"
                                )
                                # Store subscription
                                if conn not in self.subscriptions:
                                    self.subscriptions[conn] = []
                                self.subscriptions[conn].append(topic_filter)
                        # Send SUBACK
                        suback = struct.pack("!BBHB", 0x90, 0x03, packet_id, 0x00)
                        conn.send(suback)

                # Handle PINGREQ packet (type 12)
                elif packet_type == 12:
                    # Send PINGRESP
                    pingresp = struct.pack("!BB", 0xD0, 0x00)
                    conn.send(pingresp)

                # Handle DISCONNECT packet (type 14)
                elif packet_type == 14:
                    break

        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _read_remaining_length(self, conn):
        """Read MQTT remaining length field."""
        multiplier = 1
        value = 0
        while True:
            data = conn.recv(1)
            if not data:
                return 0
            byte = data[0]
            value += (byte & 0x7F) * multiplier
            if (byte & 0x80) == 0:
                break
            multiplier *= 128
        return value

    def _topic_matches(self, topic_filter, topic):
        """Check if a topic matches a topic filter (with wildcards)."""
        # Simple wildcard matching for MQTT topics
        # # matches multiple levels, + matches single level
        filter_parts = topic_filter.split("/")
        topic_parts = topic.split("/")

        i = 0
        j = 0
        while i < len(filter_parts) and j < len(topic_parts):
            if filter_parts[i] == "#":
                return True  # # matches everything after
            elif filter_parts[i] == "+":
                # + matches single level
                i += 1
                j += 1
            elif filter_parts[i] == topic_parts[j]:
                i += 1
                j += 1
            else:
                return False

        # Both must be exhausted for a match (unless filter ends with #)
        return i == len(filter_parts) and j == len(topic_parts)

    def _route_message(self, topic, payload, sender_conn):
        """Route a published message to all matching subscribers."""
        with self._messages_lock:
            self.messages.append(
                ReceivedMessage(
                    topic=topic,
                    payload=payload,
                    retain=False,
                    qos=0,
                    timestamp=time.monotonic(),
                )
            )
        # Build PUBLISH packet
        topic_bytes = topic.encode("utf-8")
        topic_len = struct.pack("!H", len(topic_bytes))

        # PUBLISH packet: fixed header + topic length + topic + payload
        remaining_length = 2 + len(topic_bytes) + len(payload)

        # Encode remaining length
        remaining_bytes = []
        while True:
            byte = remaining_length % 128
            remaining_length = remaining_length // 128
            if remaining_length > 0:
                byte |= 0x80
            remaining_bytes.append(byte)
            if remaining_length == 0:
                break

        publish_packet = (
            bytes([0x30]) + bytes(remaining_bytes) + topic_len + topic_bytes + payload
        )

        # Send to all matching subscribers
        for conn, filters in list(self.subscriptions.items()):
            if conn == sender_conn:
                continue  # Don't send back to sender
            for topic_filter in filters:
                if self._topic_matches(topic_filter, topic):
                    try:
                        conn.send(publish_packet)
                    except Exception:
                        pass
                    break  # Only send once per connection

    def stop(self):
        """Stop the broker."""
        self.running = False
        for conn in self.connections:
            try:
                conn.close()
            except Exception:
                pass
        self.connections = []
        try:
            self.sock.close()
        except Exception:
            pass
        if self.thread:
            self.thread.join(timeout=2)
