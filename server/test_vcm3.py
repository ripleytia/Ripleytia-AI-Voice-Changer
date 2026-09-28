import os, sys, json
sys.path.append(".")
from voice_changer.VoiceChangerManager import VoiceChangerManager
from voice_changer.utils.VoiceChangerParams import VoiceChangerParams

params = VoiceChangerParams(model_dir="model_dir", content_vec_500="", content_vec_500_onnx="", content_vec_500_onnx_on=False, hubert_base="", hubert_base_jp="", hubert_soft="", nsf_hifigan="", crepe_onnx_full="", crepe_onnx_tiny="", rmvpe="", rmvpe_onnx="", sample_mode="", whisper_tiny="")
vcm = VoiceChangerManager.get_instance(params)
info = vcm.get_info()
model_slot = info["modelSlots"][0] if info["modelSlots"] else {}
print("General Settings:")
for k in info:
    if k not in ["modelSlots", "sampleModels", "serverAudioInputDevices", "serverAudioOutputDevices"]:
        print(f"  {k}: {info[k]}")
print("\nSlot Settings:")
for k in model_slot:
    print(f"  {k}: {model_slot[k]}")

