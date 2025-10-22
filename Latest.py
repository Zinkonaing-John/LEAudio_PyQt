#!/usr/bin/env python3
"""
Flask Web Server for Multi-Device Audio System
Serves the HTML UI and provides API endpoints for audio control.
"""

import os
import sys
import uuid
import threading
import time
import json
from flask import Flask, render_template_string, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import tempfile
import soundfile as sf
import numpy as np
from multi_device_audio import AudioDeviceManager

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Global audio manager
audio_manager = AudioDeviceManager()
active_playbacks = {}  # Track active playback sessions


def allowed_file(filename):
    """Check if file extension is allowed."""
    ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'ogg', 'm4a', 'aac', 'wma'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Serve the main HTML page."""
    html_file = os.path.join(os.path.dirname(__file__), 'web_ui.html')
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    return html_content


@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Get list of available audio devices."""
    try:
        devices = audio_manager.discover_devices()
        device_list = []
        
        for device in devices:
            device_info = {
                'index': device.index,
                'name': device.name,
                'max_input_channels': device.max_input_channels,
                'max_output_channels': device.max_output_channels,
                'default_samplerate': device.default_samplerate,
                'is_default': device.is_default,
                'status': 'idle'
            }
            device_list.append(device_info)
        
        return jsonify({
            'success': True,
            'devices': device_list,
            'count': len(device_list)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/test-device', methods=['POST'])
def test_device():
    """Test a specific audio device."""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        
        if device_id is None:
            return jsonify({
                'success': False,
                'error': 'Device ID is required'
            }), 400
        
        # Test the device
        success = audio_manager.test_device(device_id)
        
        return jsonify({
            'success': success,
            'device_id': device_id,
            'message': 'Test passed' if success else 'Test failed'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/test-tone', methods=['POST'])
def play_test_tone():
    """Play test tone on all devices."""
    try:
        data = request.get_json()
        duration = data.get('duration', 2.0)
        frequency = data.get('frequency', 440.0)
        
        # Create test tone
        test_tone, sample_rate = audio_manager.create_test_tone(duration, frequency)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, test_tone, sample_rate)
            temp_file_path = tmp_file.name
        
        try:
            # Play on all devices
            results = audio_manager.play_on_all_devices(temp_file_path)
            
            if results:
                successful_devices = sum(results.values())
                return jsonify({
                    'success': True,
                    'devices_playing': successful_devices,
                    'total_devices': len(results),
                    'message': f'Test tone playing on {successful_devices} devices'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to play test tone on any device'
                })
        
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/play-device', methods=['POST'])
def play_on_device():
    """Play audio file on a specific device."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        device_id = request.form.get('device_id')
        
        if not file or file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type'
            }), 400
        
        if not device_id:
            return jsonify({
                'success': False,
                'error': 'Device ID is required'
            }), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
            file.save(tmp_file.name)
            temp_file_path = tmp_file.name
        
        try:
            # Load audio file
            audio_data, sample_rate = audio_manager.load_audio_file(temp_file_path)
            
            # Play on specific device
            success = audio_manager.play_on_device(int(device_id), audio_data, sample_rate)
            
            if success:
                return jsonify({
                    'success': True,
                    'device_id': device_id,
                    'message': f'Playing on device {device_id}'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Failed to play on device {device_id}'
                })
        
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/play-all', methods=['POST'])
def play_all_devices():
    """Play audio file on all devices."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        play_all = request.form.get('play_all', 'true').lower() == 'true'
        
        if not file or file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type'
            }), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
            file.save(tmp_file.name)
            temp_file_path = tmp_file.name
        
        try:
            # Generate unique playback ID
            playback_id = str(uuid.uuid4())
            
            # Play on all devices
            results = audio_manager.play_on_all_devices(temp_file_path)
            
            if results:
                successful_devices = sum(results.values())
                
                # Store playback info
                active_playbacks[playback_id] = {
                    'start_time': time.time(),
                    'file_path': temp_file_path,
                    'results': results,
                    'devices_playing': successful_devices
                }
                
                return jsonify({
                    'success': True,
                    'playback_id': playback_id,
                    'devices_playing': successful_devices,
                    'total_devices': len(results),
                    'message': f'Playing on {successful_devices} devices'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to play on any device'
                })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stop-playback', methods=['POST'])
def stop_playback():
    """Stop all audio playback."""
    try:
        data = request.get_json() or {}
        playback_id = data.get('playback_id')
        
        # Stop all playback
        audio_manager.stop_all_playback()
        
        # Clean up playback info
        if playback_id and playback_id in active_playbacks:
            playback_info = active_playbacks[playback_id]
            # Clean up temp file
            try:
                if os.path.exists(playback_info['file_path']):
                    os.unlink(playback_info['file_path'])
            except:
                pass
            del active_playbacks[playback_id]
        
        # Clean up all temp files from active playbacks
        playback_ids_to_remove = list(active_playbacks.keys())
        for pid in playback_ids_to_remove:
            if pid in active_playbacks:
                info = active_playbacks[pid]
                try:
                    if os.path.exists(info['file_path']):
                        os.unlink(info['file_path'])
                except:
                    pass
                del active_playbacks[pid]
        
        return jsonify({
            'success': True,
            'message': 'Playback stopped'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/force-stop', methods=['POST'])
def force_stop():
    """Force stop all audio playback (emergency stop)."""
    try:
        print("Force stopping all playback...")
        
        # Force stop everything with error handling
        try:
            audio_manager.stop_all_playback()
        except Exception as audio_error:
            print(f"Error stopping audio manager: {audio_error}")
            # Continue with cleanup even if audio manager fails
        
        # Clear all active playbacks safely
        playback_ids_to_clear = list(active_playbacks.keys())
        for pid in playback_ids_to_clear:
            try:
                if pid in active_playbacks:
                    playback_info = active_playbacks[pid]
                    
                    # Clean up temporary files
                    if 'file_paths' in playback_info:
                        for file_path in playback_info['file_paths']:
                            try:
                                if os.path.exists(file_path):
                                    os.unlink(file_path)
                            except Exception as file_error:
                                print(f"Error cleaning up file {file_path}: {file_error}")
                    elif 'file_path' in playback_info:
                        try:
                            if os.path.exists(playback_info['file_path']):
                                os.unlink(playback_info['file_path'])
                        except Exception as file_error:
                            print(f"Error cleaning up file {playback_info['file_path']}: {file_error}")
                    
                    del active_playbacks[pid]
            except Exception as cleanup_error:
                print(f"Error cleaning up playback {pid}: {cleanup_error}")
                # Still try to remove it
                if pid in active_playbacks:
                    del active_playbacks[pid]
        
        return jsonify({
            'success': True,
            'message': 'All playback force stopped'
        })
    
    except Exception as e:
        print(f"Error in force stop: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/play-multi-files', methods=['POST'])
def play_multi_files():
    """Play different audio files on different devices."""
    try:
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400
        
        files = request.files.getlist('files')
        device_mappings = request.form.get('device_mappings', '{}')
        
        if not files:
            return jsonify({
                'success': False,
                'error': 'No files selected'
            }), 400
        
        try:
            mappings = json.loads(device_mappings)
        except json.JSONDecodeError:
            return jsonify({
                'success': False,
                'error': 'Invalid device mappings format'
            }), 400
        
        if len(files) != len(mappings):
            return jsonify({
                'success': False,
                'error': 'Number of files must match number of device mappings'
            }), 400
        
        # Validate files and device mappings
        temp_files = []
        playback_tasks = []
        
        for i, file in enumerate(files):
            if not file or file.filename == '':
                continue
                
            if not allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'error': f'Invalid file type: {file.filename}'
                }), 400
            
            device_id = mappings.get(str(i))
            if not device_id:
                continue
            
            # Save file temporarily
            filename = secure_filename(file.filename)
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp_file:
                file.save(tmp_file.name)
                temp_files.append(tmp_file.name)
                
                playback_tasks.append({
                    'file_path': tmp_file.name,
                    'device_id': int(device_id),
                    'filename': filename
                })
        
        if not playback_tasks:
            return jsonify({
                'success': False,
                'error': 'No valid file-device mappings'
            }), 400
        
        # Start playback on each device
        results = {}
        playback_id = str(uuid.uuid4())
        
        # Create status callback for this playback session
        def status_callback(device_id, status):
            if playback_id in active_playbacks:
                active_playbacks[playback_id]['device_status'][str(device_id)] = status
        
        for task in playback_tasks:
            try:
                # Load audio file
                audio_data, sample_rate = audio_manager.load_audio_file(task['file_path'])
                
                # Play on specific device with status callback
                success = audio_manager.play_on_device(
                    task['device_id'], audio_data, sample_rate, 
                    status_callback=status_callback
                )
                
                results[task['device_id']] = {
                    'success': success,
                    'filename': task['filename']
                }
                
            except Exception as e:
                results[task['device_id']] = {
                    'success': False,
                    'error': str(e),
                    'filename': task['filename']
                }
        
        # Store playback info
        active_playbacks[playback_id] = {
            'start_time': time.time(),
            'file_paths': [task['file_path'] for task in playback_tasks],
            'results': results,
            'type': 'multi_file',
            'device_status': {str(task['device_id']): 'Playing' for task in playback_tasks if results.get(task['device_id'], {}).get('success', False)}
        }
        
        successful_devices = sum(1 for r in results.values() if r['success'])
        
        return jsonify({
            'success': True,
            'playback_id': playback_id,
            'devices_playing': successful_devices,
            'total_devices': len(results),
            'results': results,
            'message': f'Playing different files on {successful_devices} devices'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/playback-status', methods=['GET'])
def get_playback_status():
    """Get current playback status for all devices."""
    try:
        status = audio_manager.get_device_status()
        
        # Check if we have active multi-file playbacks
        multi_file_playing = False
        for playback_info in active_playbacks.values():
            if playback_info.get('type') == 'multi_file':
                # Check if any devices are still playing
                device_status = playback_info.get('device_status', {})
                if any(status == 'Playing' for status in device_status.values()):
                    multi_file_playing = True
                    break
        
        # Update status for multi-file playbacks
        if multi_file_playing:
            for playback_info in active_playbacks.values():
                if playback_info.get('type') == 'multi_file':
                    device_status = playback_info.get('device_status', {})
                    # Update the main status with multi-file device statuses
                    for device_id, device_status_value in device_status.items():
                        if device_id in status:
                            status[device_id] = device_status_value
        
        return jsonify({
            'success': True,
            'devices': status,
            'is_playing': audio_manager.is_playing or multi_file_playing
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload for testing."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if not file or file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file type'
            }), 400
        
        # Save file
        filename = secure_filename(file.filename)
        upload_path = os.path.join('uploads', filename)
        os.makedirs('uploads', exist_ok=True)
        file.save(upload_path)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': upload_path,
            'message': 'File uploaded successfully'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    return jsonify({
        'success': False,
        'error': 'File too large. Maximum size is 100MB.'
    }), 413


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


def cleanup_temp_files():
    """Cleanup temporary files periodically."""
    while True:
        time.sleep(300)  # Clean up every 5 minutes
        try:
            # Clean up old playback files
            current_time = time.time()
            to_remove = []
            
            for playback_id, info in active_playbacks.items():
                if current_time - info['start_time'] > 600:  # 10 minutes old
                    to_remove.append(playback_id)
            
            for playback_id in to_remove:
                info = active_playbacks[playback_id]
                try:
                    if os.path.exists(info['file_path']):
                        os.unlink(info['file_path'])
                except:
                    pass
                del active_playbacks[playback_id]
        
        except Exception as e:
            print(f"Error in cleanup: {e}")


if __name__ == '__main__':
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_temp_files, daemon=True)
    cleanup_thread.start()
    
    # Initialize audio manager
    print("Initializing audio manager...")
    audio_manager.discover_devices()
    
    # Start Flask server
    print("Starting Flask server...")
    print("Open your browser and go to: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
