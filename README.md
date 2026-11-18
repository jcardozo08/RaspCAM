# RaspCAM

Sistema de **câmera de bordo** para foguetes, baseado em Raspberry Pi. Ele grava vídeo Full HD com áudio do início ao fim do voo e registra dados de voo em paralelo. Foi pensado para funcionar sozinho dentro do foguete, sem intervenção: liga, aguarda, grava, sobrevive a falhas e desliga com segurança.

## Funcionalidades

- **Gravação 1080p30 + áudio** com câmera Arducam 8MP via **GStreamer**, com fallback automático para **FFmpeg** se o gravador principal falhar
- **Vídeo segmentado** em arquivos de 1 minuto: um corte de energia no impacto perde no máximo o segmento atual
- **Gestão de armazenamento:** monitora o espaço livre e apaga os segmentos mais antigos quando o cartão enche
- **Máquina de estados de voo** com barômetro BMP280 (pressão/altitude), registrada em CSV junto com o FPS medido e o espaço livre
- **Avisos sonoros** por buzzer (sistema iniciado, gravando, erro, pós-pouso para localização)
- **Gerenciamento de energia** por GPIO e desligamento seguro do Raspberry Pi
- Ajuste manual de exposição e de outros parâmetros da câmera via v4l2
- `juntador_de_video.py` une os segmentos num único vídeo depois do voo

**Stack:** Python · gpiozero · GStreamer · FFmpeg · v4l2 · Raspberry Pi

**Hardware:** placa de interface [CAMERA_RASP](https://github.com/jcardozo08/CAMERA_RASP)
