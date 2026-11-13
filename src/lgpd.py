"""Apoio à LGPD: consentimento antes do uso e retenção mínima (apagar áudios temporários)."""
import glob, os, shutil

from .config import AVISO_CONSENTIMENTO


def aviso():
    return AVISO_CONSENTIMENTO


def apagar_temporarios(pasta):
    """Remove os áudios de resposta gerados (a voz sintetizada não é dado pessoal, mas não precisa ficar guardada)."""
    for f in glob.glob(os.path.join(pasta, "*.wav")):
        try:
            os.remove(f)
        except OSError:
            pass
