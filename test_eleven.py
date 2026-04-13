from config import settings
from src.services.asr_service import ElevenLabsASRService
try:
    asr = ElevenLabsASRService(settings.elevenlabs_api_key)
    print('Testing ElevenLabs API...')
    res = asr.transcribe(r'C:\Users\Ibrahim\OneDrive\Documents\recordings\outputt.wav')
    print('Result:', res)
except Exception as e:
    print('ERROR:', e)
