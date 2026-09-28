import os, sys
sys.path.append(".")
from voice_changer.VoiceChangerManager import VoiceChangerManager
from voice_changer.utils.VoiceChangerParams import VoiceChangerParams

params = VoiceChangerParams(
    model_dir="model_dir",
    content_vec_500="content_vec_500.pt",
    content_vec_500_onnx="content_vec_500.onnx",
    content_vec_500_onnx_on=False,
    hubert_base="hubert_base.pt",
    hubert_base_jp="hubert_base_jp.pt",
    hubert_soft="hubert_soft.pt",
    nsf_hifigan="nsf_hifigan.pt",
    crepe_onnx_full="crepe_onnx_full.onnx",
    crepe_onnx_tiny="crepe_onnx_tiny.onnx",
    rmvpe="rmvpe.pt",
    rmvpe_onnx="rmvpe.onnx",
    sample_mode="",
    whisper_tiny="whisper_tiny.pt",
)

vcm = VoiceChangerManager.get_instance(params)
print("VCM started successfully!")
