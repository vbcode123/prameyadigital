"""
Real-time RTMP Streaming Relay Engine for Prameya Digital Newsroom.
Receives incoming live video chunks from Reporter's mobile browser (WebM / MediaRecorder)
and transcodes / relays them via FFmpeg to YouTube Live & Facebook Live RTMP endpoints.
"""

import os
import sys
import shutil
import logging
import subprocess
import threading
import time
from pathlib import Patha

logger = logging.getLogger(__name__)

class RelaySession:
    def __init__(self, session_id, target_urls):
        self.session_id = session_id
        self.target_urls = target_urls # list of RTMP URLs
        self.process = None
        self.lock = threading.RLock()
        self.is_active = False
        self.chunks_received = 0
        self.bytes_relayed = 0
        self.started_at = None
        self.error_message = None
        self.latest_preview_frame = None
        self.latest_preview_time = 0
        self.ffmpeg_path = shutil.which('ffmpeg') or 'ffmpeg'

    def start(self):
        with self.lock:
            if self.is_active and self.process and self.process.poll() is None:
                return True

            if not shutil.which('ffmpeg'):
                self.error_message = "FFmpeg is not installed on this server. Install via 'sudo apt install -y ffmpeg'."
                logger.error(f"[Relay {self.session_id}] {self.error_message}")
                return False

            if not self.target_urls:
                self.error_message = "No valid RTMP destination URL or stream key configured."
                logger.error(f"[Relay {self.session_id}] {self.error_message}")
                return False

            try:
                # Build FFmpeg command for low-latency live broadcast
                # Primary RTMP target (YouTube / Facebook)
                primary_url = self.target_urls[0]

                cmd = [
                    self.ffmpeg_path,
                    '-y',
                    '-loglevel', 'warning',
                    '-re',                          # Ingest at real-time pace
                    '-f', 'webm',                   # Browser MediaRecorder container
                    '-i', 'pipe:0',                 # Read chunks from stdin
                    '-c:v', 'libx264',              # H.264 video codec required by YouTube/FB
                    '-preset', 'veryfast',          # Fast encoding for real-time
                    '-tune', 'zerolatency',         # Low latency tuning
                    '-r', '30',                     # 30 fps
                    '-g', '60',                     # Keyframe every 2 seconds (mandatory for YouTube)
                    '-keyint_min', '30',
                    '-b:v', '2500k',                # 2.5 Mbps 720p broadcast bitrate
                    '-maxrate', '2800k',
                    '-bufsize', '5000k',
                    '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac',                  # AAC audio
                    '-b:a', '128k',
                    '-ar', '44100',
                    '-ac', '2'
                ]

                if len(self.target_urls) > 1:
                    # Multi-destination broadcast (YouTube + Facebook) via tee muxer
                    tee_targets = "|".join([f"[f=flv:onfail=ignore]{url}" for url in self.target_urls])
                    cmd.extend(['-f', 'tee', '-map', '0:v', '-map', '0:a', tee_targets])
                else:
                    cmd.extend(['-f', 'flv', primary_url])

                # Launch FFmpeg process with piped stdin
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )

                self.is_active = True
                self.started_at = time.time()
                self.chunks_received = 0
                self.bytes_relayed = 0
                self.error_message = None

                logger.info(f"[Relay {self.session_id}] FFmpeg relay launched successfully to {primary_url.split('/')[:3]}")
                return True

            except FileNotFoundError:
                self.error_message = "FFmpeg executable not found in system PATH."
                logger.error(f"[Relay {self.session_id}] {self.error_message}")
                self.is_active = False
                return False
            except Exception as e:
                self.error_message = str(e)
                logger.error(f"[Relay {self.session_id}] Failed to start FFmpeg relay: {e}", exc_info=True)
                self.is_active = False
                return False

    def write_chunk(self, chunk_bytes):
        with self.lock:
            if not self.is_active or not self.process:
                # Try starting if not started
                started = self.start()
                if not started:
                    return False, self.error_message or "Failed to initialize relay"

            # Check if FFmpeg has crashed or exited
            poll_code = self.process.poll()
            if poll_code is not None:
                _, err_out = self.process.communicate()
                err_str = err_out.decode('utf-8', errors='ignore') if err_out else f"Process exited with code {poll_code}"
                self.is_active = False
                self.error_message = f"FFmpeg relay exited: {err_str[-200:]}"
                logger.warning(f"[Relay {self.session_id}] {self.error_message}")
                return False, self.error_message

            try:
                self.process.stdin.write(chunk_bytes)
                self.process.stdin.flush()
                self.chunks_received += 1
                self.bytes_relayed += len(chunk_bytes)
                return True, "Chunk relayed"
            except (BrokenPipeError, OSError) as e:
                self.is_active = False
                self.error_message = f"Relay broken pipe (stream disconnected): {e}"
                logger.error(f"[Relay {self.session_id}] {self.error_message}")
                return False, self.error_message

    def stop(self):
        with self.lock:
            self.is_active = False
            if self.process:
                try:
                    if self.process.stdin:
                        self.process.stdin.close()
                    self.process.wait(timeout=2)
                except Exception:
                    try:
                        self.process.terminate()
                        self.process.wait(timeout=1)
                    except Exception:
                        self.process.kill()
                finally:
                    self.process = None
            logger.info(f"[Relay {self.session_id}] FFmpeg relay stopped. Total chunks: {self.chunks_received}, bytes: {self.bytes_relayed}")


class StreamingRelayManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StreamingRelayManager, cls).__new__(cls)
                cls._instance.sessions = {}
            return cls._instance

    def _get_target_urls(self, destination='youtube'):
        from app.models import LiveStreamSetting
        setting = LiveStreamSetting.objects.first()
        if not setting:
            return []

        urls = []
        # YouTube endpoint
        if destination in ('youtube', 'youtube_facebook'):
            if setting.youtube_rtmp_url and setting.youtube_stream_key:
                base_url = setting.youtube_rtmp_url.strip().rstrip('/')
                key = setting.youtube_stream_key.strip()
                urls.append(f"{base_url}/{key}")

        # Facebook endpoint
        if destination in ('facebook', 'youtube_facebook'):
            if setting.facebook_rtmp_url and setting.facebook_stream_key:
                base_url = setting.facebook_rtmp_url.strip().rstrip('/')
                key = setting.facebook_stream_key.strip()
                urls.append(f"{base_url}/{key}")

        return urls

    def start_session(self, session_id, destination='youtube'):
        session_id = str(session_id)
        target_urls = self._get_target_urls(destination)
        if not target_urls:
            logger.warning(f"No stream keys configured for destination '{destination}'")
            return False, "No stream key configured. Please configure in Stream Keys (YT/FB)."

        relay = RelaySession(session_id, target_urls)
        self.sessions[session_id] = relay
        started = relay.start()
        return started, relay.error_message if not started else "Relay started"

    def write_chunk(self, session_id, chunk_bytes, destination='youtube'):
        session_id = str(session_id)
        relay = self.sessions.get(session_id)
        if not relay:
            # Auto-create if not pre-started
            target_urls = self._get_target_urls(destination)
            if not target_urls:
                return False, "No stream key configured for live streaming."
            relay = RelaySession(session_id, target_urls)
            self.sessions[session_id] = relay

        return relay.write_chunk(chunk_bytes)

    def stop_session(self, session_id):
        session_id = str(session_id)
        if hasattr(self, '_previews'):
            self._previews.pop(session_id, None)
        relay = self.sessions.pop(session_id, None)
        if relay:
            relay.stop()
            return True
        return False

    def update_preview(self, session_id, frame_b64):
        session_id = str(session_id)
        if not hasattr(self, '_previews'):
            self._previews = {}
        self._previews[session_id] = frame_b64
        relay = self.sessions.get(session_id)
        if relay:
            relay.latest_preview_frame = frame_b64
            relay.latest_preview_time = time.time()

    def get_preview(self, session_id):
        session_id = str(session_id)
        relay = self.sessions.get(session_id)
        if relay and relay.latest_preview_frame:
            return relay.latest_preview_frame
        if hasattr(self, '_previews'):
            return self._previews.get(session_id)
        return None

    def get_status(self, session_id):
        session_id = str(session_id)
        relay = self.sessions.get(session_id)
        if not relay:
            return {
                'active': False,
                'chunks_received': 0,
                'bytes_relayed': 0,
                'ffmpeg_installed': bool(shutil.which('ffmpeg')),
                'error': None
            }
        return {
            'active': relay.is_active,
            'chunks_received': relay.chunks_received,
            'bytes_relayed': relay.bytes_relayed,
            'ffmpeg_installed': bool(shutil.which('ffmpeg')),
            'error': relay.error_message
        }


# Global relay manager instance
relay_manager = StreamingRelayManager()
