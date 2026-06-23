# Setup Notes — HokkienTTS (Phase 1 working)

Hard-won setup details so a reinstall / new machine doesn't have to rediscover them.

## Environment

- **Python 3.11** (NOT 3.13 — `coqui-tts-pygoruut` requires `<3.13`). Installed alongside
  3.13; selected via the `py -3.11` launcher.
- Virtual env: `hokkien_speech_env\` (created with `py -3.11 -m venv hokkien_speech_env`).
- Run things with the venv's Python directly:
  `hokkien_speech_env\Scripts\python.exe ...`
  (or activate once: `.\hokkien_speech_env\Scripts\Activate.ps1`)

## Install order (matters)

1. GPU PyTorch FIRST (so we get the CUDA build, not CPU-only):
   `python -m pip install --use-feature=truststore torch torchaudio --index-url https://download.pytorch.org/whl/cu124`
2. `python -m pip install --use-feature=truststore coqui-tts-pygoruut`
3. Pin transformers back to 4.x (5.x removes a function Coqui needs):
   `python -m pip install --use-feature=truststore "transformers>=4.52.1,<5"`
4. `python -m pip install --use-feature=truststore pip-system-certs`

Verify GPU: `python -c "import torch; print(torch.cuda.is_available())"` → should print `True`.

## Norton / SSL gotchas

Norton scans HTTPS by presenting its own certificate, which Python's downloaders don't trust
by default → `CERTIFICATE_VERIFY_FAILED`.

- **pip:** add `--use-feature=truststore` to every install (uses the Windows cert store).
- **Other Python downloads (goruut binary, Hugging Face):** `pip-system-certs` makes ALL
  Python HTTPS in this venv use the Windows cert store. Install it once (step 4).
- Norton may also flag `IDP.Generic` ("command-line detection") on installers — a false
  positive; allow it.

## goruut (phonemizer) Windows fix

`coqui-tts-pygoruut`'s wrapper instantiates goruut with `writeable_bin_dir=''`, which uses a
temp folder whose `goruut.exe` can't be deleted while running (`WinError 5: Access is denied`).

- Patched: `hokkien_speech_env\Lib\site-packages\TTS\tts\utils\text\phonemizers\pygoruut_wrapper.py`
  to use a persistent folder (`~/.goruut_bin`, overridable via `GORUUT_BIN_DIR`).
- **This patch is lost if you reinstall/upgrade `coqui-tts-pygoruut`** — reapply it.

## Model

- SuiSiann VITS weights in `models\suisiann\` (`best_model.pth` ~952 MB, `config.json`).
- Phoneme-based; phonemizer `pygoruut:v0.6.3`, language `MinnanHokkien2`. Takes Hàn-jī directly.

## Run Phase 1

```
set PYTHONUTF8=1            # so Chinese/IPA prints to the console
hokkien_speech_env\Scripts\python.exe phase1_tts.py
```
Outputs the IPA diagnostic + `test_native_hokkien.wav`. (UTF-8 is needed or printing the
Chinese/IPA text crashes with a charmap error.)
