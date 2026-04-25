"""
Simplified MQTT broker for testing.
Based on paho-mqtt test broker but with minimal dependencies.
"""

import socket
import struct
import threading
import time
from dataclasses import dataclass
from typing import Dict, List


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
            clean_disconnect = False
            while self.running:
                # Read fixed header byte
                data = conn.recv(1)
                if not data:
                    break

                packet_type = data[0] >> 4

                # Handle CONNECT packet (type 1)
                if packet_type == 1:
                    remaining = self._read_remaining_length(conn)
                    connect_data = conn.recv(remaining) if remaining > 0 else b""
                    will = self._parse_will(connect_data)
                    if will:
                        self.wills[conn] = will
                    connack = struct.pack("!BBBB", 0x20, 0x02, 0x00, 0x00)
                    conn.send(connack)

                # Handle PUBLISH packet (type 3)
                elif packet_type == 3:
                    retain_flag = bool(data[0] & 0x01)
                    qos_val = (data[0] >> 1) & 0x03
                    remaining = self._read_remaining_length(conn)
                    if remaining > 0:
                        publish_data = conn.recv(remaining)
                        if len(publish_data) >= 2:
                            topic_len = struct.unpack("!H", publish_data[:2])[0]
                            if len(publish_data) >= 2 + topic_len:
                                topic = publish_data[2 : 2 + topic_len].decode("utf-8")
                                offset = 2 + topic_len
                                # Skip packet ID for QoS 1/2
                                if qos_val > 0:
                                    packet_id = struct.unpack(
                                        "!H", publish_data[offset : offset + 2]
                                    )[0]
                                    offset += 2
                                else:
                                    packet_id = None
                                payload = publish_data[offset:]
                                self._route_message(
                                    topic, payload, conn, retain_flag, qos_val
                                )
                                # Send PUBACK for QoS 1, PUBREC for QoS 2
                                if qos_val == 1 and packet_id is not None:
                                    puback = struct.pack("!BBH", 0x40, 0x02, packet_id)
                                    try:
                                        conn.send(puback)
                                    except Exception:
                                        pass
                                elif qos_val == 2 and packet_id is not None:
                                    pubrec = struct.pack("!BBH", 0x50, 0x02, packet_id)
                                    try:
                                        conn.send(pubrec)
                                    except Exception:
                                        pass

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
                                # Replay matching retained messages
                                for ret_topic, ret_payload in list(
                                    self.retained.items()
                                ):
                                    if self._topic_matches(topic_filter, ret_topic):
                                        ret_topic_bytes = ret_topic.encode("utf-8")
                                        ret_topic_len_bytes = struct.pack(
                                            "!H", len(ret_topic_bytes)
                                        )
                                        # Set retain bit in fixed header: 0x31
                                        rem_len = (
                                            2 + len(ret_topic_bytes) + len(ret_payload)
                                        )
                                        rem_bytes = []
                                        while True:
                                            byte = rem_len % 128
                                            rem_len = rem_len // 128
                                            if rem_len > 0:
                                                byte |= 0x80
                                            rem_bytes.append(byte)
                                            if rem_len == 0:
                                                break
                                        retained_packet = (
                                            bytes([0x31])
                                            + bytes(rem_bytes)
                                            + ret_topic_len_bytes
                                            + ret_topic_bytes
                                            + ret_payload
                                        )
                                        try:
                                            conn.send(retained_packet)
                                        except Exception:
                                            pass
                        # Send SUBACK
                        suback = struct.pack("!BBHB", 0x90, 0x03, packet_id, 0x00)
                        conn.send(suback)

                # Handle PINGREQ packet (type 12)
                elif packet_type == 12:
                    self._read_remaining_length(conn)  # drain 0x00
                    # Send PINGRESP
                    pingresp = struct.pack("!BB", 0xD0, 0x00)
                    conn.send(pingresp)

                # Handle DISCONNECT packet (type 14)
                elif packet_type == 14:
                    self._read_remaining_length(conn)  # drain 0x00
                    clean_disconnect = True
                    break

        except Exception:
            pass
        finally:
            if not clean_disconnect:
                will = self.wills.pop(conn, None)
                if will:
                    self._route_message(
                        will.topic, will.payload, conn, retain=will.retain, qos=will.qos
                    )
            else:
                self.wills.pop(conn, None)
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

    def _parse_will(self, connect_data):
        """Parse will from CONNECT payload. Returns WillMessage or None."""
        try:
            proto_len = struct.unpack("!H", connect_data[:2])[0]
            offset = 2 + proto_len  # skip protocol name bytes
            offset += 1  # skip protocol level
            connect_flags = connect_data[offset]
            offset += 1  # skip connect flags
            offset += 2  # skip keep-alive

            will_flag = bool(connect_flags & 0x04)
            will_qos = (connect_flags >> 3) & 0x03
            will_retain = bool(connect_flags & 0x20)

            # skip client ID
            client_id_len = struct.unpack("!H", connect_data[offset : offset + 2])[0]
            offset += 2 + client_id_len

            if not will_flag:
                return None

            will_topic_len = struct.unpack("!H", connect_data[offset : offset + 2])[0]
            offset += 2
            will_topic = connect_data[offset : offset + will_topic_len].decode("utf-8")
            offset += will_topic_len

            will_payload_len = struct.unpack("!H", connect_data[offset : offset + 2])[0]
            offset += 2
            will_payload = connect_data[offset : offset + will_payload_len]

            return WillMessage(
                topic=will_topic,
                payload=will_payload,
                retain=will_retain,
                qos=will_qos,
            )
        except Exception:
            return None

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

    def _route_message(self, topic, payload, sender_conn, retain=False, qos=0):
        """Route a published message to all matching subscribers."""
        # Update retained store
        if retain:
            if payload:
                self.retained[topic] = payload
            else:
                self.retained.pop(topic, None)

        # Record in inspection list
        with self._messages_lock:
            self.messages.append(
                ReceivedMessage(
                    topic=topic,
                    payload=payload,
                    retain=retain,
                    qos=qos,
                    timestamp=time.monotonic(),
                )
            )

        # Build PUBLISH packet (QoS 0 delivery to subscribers)
        topic_bytes = topic.encode("utf-8")
        topic_len = struct.pack("!H", len(topic_bytes))
        remaining_length = 2 + len(topic_bytes) + len(payload)
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

        # Send to all matching subscribers (except sender)
        for conn, filters in list(self.subscriptions.items()):
            if conn == sender_conn:
                continue
            for topic_filter in filters:
                if self._topic_matches(topic_filter, topic):
                    try:
                        conn.send(publish_packet)
                    except Exception:
                        pass
                    break

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
