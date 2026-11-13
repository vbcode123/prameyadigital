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
from pathlib import Path

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
        self.log_file = None
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
                    '-f', 'webm',                   # Browser MediaRecorder container (real-time stream)
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

                # Pipe stderr to log file to avoid OS buffer deadlocks (prevent pipe freezing)
                import tempfile
                log_path = Path(tempfile.gettempdir()) / f"ffmpeg_camera_{self.session_id}.log"
                self.log_file = open(log_path, 'wb')

                # Launch FFmpeg process with piped stdin and file-backed stderr
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=self.log_file
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
                err_str = f"Process exited with code {poll_code}"
                try:
                    if hasattr(self, 'log_file') and self.log_file:
                        self.log_file.flush()
                        with open(self.log_file.name, 'r', errors='ignore') as lf:
                            err_str = lf.read()[-300:] or err_str
                except Exception:
                    pass
                self.is_active = False
                self.error_message = f"FFmpeg relay exited: {err_str}"
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

            if hasattr(self, 'log_file') and self.log_file and not self.log_file.closed:
                try:
                    self.log_file.close()
                except Exception:
                    pass

            logger.info(f"[Relay {self.session_id}] FFmpeg relay stopped. Total chunks: {self.chunks_received}, bytes: {self.bytes_relayed}")


def generate_broadcast_overlay(output_path, headline="Live Coverage", district="", reporter_name="", logo_path=None):
    """
    Generates a 1280x720 transparent RGBA broadcast plate containing:
      - Top-right: Prameya Digital logo (scaled, crisp)
      - Top-left: Crimson red LIVE pill badge
      - Bottom-left: Reporter Name & District identification chip
      - Bottom: Sleek dark lower-third strap with red BREAKING tag & headline text.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        overlay = Image.new('RGBA', (1280, 720), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # 1. Top-Right: Logo
        if not logo_path or not os.path.exists(logo_path):
            base_dir = Path(__file__).resolve().parent
            logo_path = os.path.join(base_dir, 'static', 'images', 'liveimage.png')
            if not os.path.exists(logo_path):
                logo_path = os.path.join(base_dir, 'static', 'images', 'prameya.png')

        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert('RGBA')
                logo.thumbnail((160, 75), Image.Resampling.LANCZOS)
                lx = 1280 - logo.width - 35
                ly = 25

                # Rounded corner mask for clean TV badge look
                mask = Image.new('L', logo.size, 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, logo.width - 1, logo.height - 1], radius=8, fill=255)

                draw.rounded_rectangle([lx - 6, ly - 4, lx + logo.width + 6, ly + logo.height + 4], radius=10, fill=(255, 255, 255, 255), outline=(220, 38, 38, 240), width=2)
                overlay.paste(logo, (lx, ly), mask=mask)
            except Exception as e:
                logger.warning(f"Failed to paste logo on overlay: {e}")

        # Font loaders
        font_bold = None
        for p in ['C:/Windows/Fonts/arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf']:
            if os.path.exists(p):
                try:
                    font_bold = ImageFont.truetype(p, 20)
                    break
                except Exception:
                    pass
        if not font_bold:
            font_bold = ImageFont.load_default()

        # 2. Top-Left: LIVE Badge
        draw.rounded_rectangle([35, 25, 155, 68], radius=8, fill=(220, 38, 38, 240))
        draw.ellipse([48, 38, 62, 52], fill=(255, 255, 255, 255))
        draw.text((70, 35), 'LIVE', fill=(255, 255, 255, 255), font=font_bold)

        # Text Font
        text_font = None
        for p in ['C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/freefont/FreeSans.ttf']:
            if os.path.exists(p):
                try:
                    text_font = ImageFont.truetype(p, 19)
                    break
                except Exception:
                    pass
        if not text_font:
            text_font = ImageFont.load_default()

        # 3. Reporter Name & District Chip (above strap)
        if reporter_name:
            rep_text = f"🎤  {reporter_name}" + (f"  |  {district.upper()}" if district else "")
            chip_w = min(480, max(220, len(rep_text) * 11 + 30))
            draw.rounded_rectangle([40, 598, 40 + chip_w, 636], radius=6, fill=(15, 23, 42, 235))
            draw.rectangle([40, 598, 46, 636], fill=(245, 158, 11, 255))
            draw.text((56, 608), rep_text, fill=(248, 250, 252, 255), font=text_font)

        # 4. Bottom Strap
        draw.rectangle([0, 645, 1280, 705], fill=(15, 23, 42, 235))
        draw.rectangle([0, 642, 1280, 645], fill=(245, 158, 11, 255))
        draw.rectangle([0, 645, 175, 705], fill=(220, 38, 38, 255))
        draw.text((25, 662), 'BREAKING', fill=(255, 255, 255, 255), font=font_bold)

        disp_text = f"{district.upper()} | {headline}" if (district and not reporter_name) else headline
        if len(disp_text) > 85:
            disp_text = disp_text[:82] + "..."

        draw.text((195, 662), disp_text, fill=(255, 255, 255, 255), font=text_font)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        overlay.save(output_path, format='PNG')
        return True, output_path
    except Exception as e:
        logger.error(f"Error generating broadcast overlay: {e}", exc_info=True)
        return False, str(e)


class RecordedRelaySession:
    """
    Broadcasts a pre-recorded video file (MP4/WebM) to RTMP live destinations (YouTube/Facebook)
    in real time (-re), with optional TV news overlay (Prameya logo, LIVE badge, Breaking strap).
    """
    def __init__(self, session_id, video_path, target_urls, overlay_graphics=True, headline='', district='', reporter_name=''):
        self.session_id = str(session_id)
        self.video_path = str(video_path)
        self.target_urls = target_urls
        self.overlay_graphics = overlay_graphics
        self.headline = headline or "Live Broadcast"
        self.district = district or ""
        self.reporter_name = reporter_name or ""
        self.process = None
        self.lock = threading.RLock()
        self.is_active = False
        self.started_at = None
        self.error_message = None
        self.latest_preview_frame = None
        self.latest_preview_time = 0
        self.ffmpeg_path = shutil.which('ffmpeg') or 'ffmpeg'
        self.overlay_path = None
        self.monitor_thread = None
        self.log_file = None
        self.is_recorded = True

    def start(self):
        with self.lock:
            if self.is_active and self.process and self.process.poll() is None:
                return True

            if not shutil.which('ffmpeg'):
                self.error_message = "FFmpeg is not installed on this server. Install via 'sudo apt install -y ffmpeg'."
                logger.error(f"[RecordedRelay {self.session_id}] {self.error_message}")
                return False

            if not os.path.exists(self.video_path):
                self.error_message = f"Source video file not found at {self.video_path}"
                logger.error(f"[RecordedRelay {self.session_id}] {self.error_message}")
                return False

            if not self.target_urls:
                self.error_message = "No valid RTMP destination URL or stream key configured."
                logger.error(f"[RecordedRelay {self.session_id}] {self.error_message}")
                return False

            primary_url = self.target_urls[0]

            # Generate overlay if requested
            self.overlay_path = None
            if self.overlay_graphics:
                import tempfile
                ov_path = os.path.join(tempfile.gettempdir(), f"overlay_{self.session_id}.png")
                ok, res = generate_broadcast_overlay(
                    ov_path,
                    headline=self.headline,
                    district=self.district,
                    reporter_name=self.reporter_name
                )
                if ok:
                    self.overlay_path = ov_path
                    try:
                        import base64
                        with open(ov_path, 'rb') as f:
                            self.latest_preview_frame = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('utf-8')
                            self.latest_preview_time = time.time()
                    except Exception:
                        pass

            cmd = [
                self.ffmpeg_path,
                '-y',
                '-loglevel', 'warning',
                '-re',                          # Ingest at native real-time speed
                '-i', self.video_path,
            ]

            if self.overlay_path and os.path.exists(self.overlay_path):
                cmd.extend(['-i', self.overlay_path])
                filter_str = (
                    '[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2[scaled]; '
                    '[scaled][1:v]overlay=0:0[outv]'
                )
            else:
                filter_str = '[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2[outv]'

            cmd.extend([
                '-filter_complex', filter_str,
                '-map', '[outv]',
                '-map', '0:a?',
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-tune', 'zerolatency',
                '-r', '30',
                '-g', '60',
                '-keyint_min', '30',
                '-b:v', '2500k',
                '-maxrate', '2800k',
                '-bufsize', '5000k',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-ar', '44100',
                '-ac', '2'
            ])

            if len(self.target_urls) > 1:
                tee_targets = "|".join([f"[f=flv:onfail=ignore]{url}" for url in self.target_urls])
                cmd.extend(['-f', 'tee', tee_targets])
            else:
                cmd.extend(['-f', 'flv', primary_url])

            try:
                import tempfile
                log_path = Path(tempfile.gettempdir()) / f"ffmpeg_recorded_{self.session_id}.log"
                self.log_file = open(log_path, 'wb')

                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=self.log_file
                )

                self.is_active = True
                self.started_at = time.time()
                self.error_message = None

                self.monitor_thread = threading.Thread(target=self._monitor_stream, daemon=True)
                self.monitor_thread.start()

                logger.info(f"[RecordedRelay {self.session_id}] FFmpeg stream started for {self.video_path} to {primary_url.split('/')[:3]}")
                return True
            except Exception as e:
                self.error_message = str(e)
                logger.error(f"[RecordedRelay {self.session_id}] Failed to start: {e}", exc_info=True)
                self.is_active = False
                return False

    def _monitor_stream(self):
        while self.is_active and self.process:
            poll_code = self.process.poll()
            if poll_code is not None:
                logger.info(f"[RecordedRelay {self.session_id}] FFmpeg completed with returncode {poll_code}")
                break
            time.sleep(1.0)

        with self.lock:
            self.is_active = False
            if self.log_file and not self.log_file.closed:
                try:
                    self.log_file.close()
                except Exception:
                    pass
            if self.overlay_path and os.path.exists(self.overlay_path):
                try:
                    os.remove(self.overlay_path)
                except Exception:
                    pass

        try:
            from django.utils import timezone
            from app.models import LiveBroadcastSession
            LiveBroadcastSession.objects.filter(pk=self.session_id, status='live').update(
                status='ended',
                ended_at=timezone.now(),
                current_cue='Recorded broadcast playback completed.'
            )
        except Exception as e:
            logger.warning(f"[RecordedRelay {self.session_id}] DB status update failed: {e}")

    def stop(self):
        with self.lock:
            self.is_active = False
            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=2)
                except Exception:
                    try:
                        self.process.kill()
                    except Exception:
                        pass
                finally:
                    self.process = None

            if self.log_file and not self.log_file.closed:
                try:
                    self.log_file.close()
                except Exception:
                    pass

            if self.overlay_path and os.path.exists(self.overlay_path):
                try:
                    os.remove(self.overlay_path)
                except Exception:
                    pass


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

    def start_recorded_session(self, session_id, video_path, destination='youtube', overlay_graphics=True, headline='', district='', reporter_name=''):
        session_id = str(session_id)
        target_urls = self._get_target_urls(destination)
        if not target_urls:
            return False, "No stream key configured. Please configure in Stream Keys (YT/FB)."

        relay = RecordedRelaySession(
            session_id=session_id,
            video_path=video_path,
            target_urls=target_urls,
            overlay_graphics=overlay_graphics,
            headline=headline,
            district=district,
            reporter_name=reporter_name
        )
        self.sessions[session_id] = relay
        started = relay.start()
        return started, relay.error_message if not started else "Recorded relay started"

    def write_chunk(self, session_id, chunk_bytes, destination='youtube'):
        session_id = str(session_id)
        relay = self.sessions.get(session_id)
        if not relay:
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
                'is_recorded': False,
                'chunks_received': 0,
                'bytes_relayed': 0,
                'ffmpeg_installed': bool(shutil.which('ffmpeg')),
                'error': None
            }
        is_rec = getattr(relay, 'is_recorded', False)
        elapsed = int(time.time() - relay.started_at) if (relay.started_at and relay.is_active) else 0
        return {
            'active': relay.is_active,
            'is_recorded': is_rec,
            'elapsed_seconds': elapsed,
            'chunks_received': getattr(relay, 'chunks_received', 0),
            'bytes_relayed': getattr(relay, 'bytes_relayed', 0),
            'ffmpeg_installed': bool(shutil.which('ffmpeg')),
            'error': relay.error_message
        }


# Global relay manager instance
relay_manager = StreamingRelayManager()
