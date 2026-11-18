import sys
import time
import signal
import shutil
import random
import csv
import subprocess
import threading

from pathlib import Path
from datetime import datetime
from collections import deque

from gpiozero import Buzzer, OutputDevice, DigitalInputDevice


# ============================================================
# CONFIGURACOES
# ============================================================


# ============================================================
# GRAVADOR
# ============================================================

GRAVADOR_PRINCIPAL = "gstreamer"     # "gstreamer" ou "ffmpeg"
GRAVADOR_FALLBACK = "ffmpeg"         # "gstreamer", "ffmpeg" ou None

VIDEO_DEVICE = (
    "/dev/v4l/by-id/"
    "usb-Arducam_Technology_Co.__Ltd._Arducam_8mp_SN0001-video-index0"
)
AUDIO_DEVICE = "hw:CARD=Arducam8mp,DEV=0"

WIDTH = 1920
HEIGHT = 1080
FPS = 30

AUDIO_BITRATE = "128k"

SEGMENTO_SEGUNDOS = 60

PASTA_BASE = Path.home() / "Desktop" / "Gravacoes"


# ============================================================
# CAMERA
# ============================================================

CAMERA_CONFIG_HABILITADA = True


# ------------------------------------------------------------
# Exposicao
# ------------------------------------------------------------

# 1 = Manual Mode
# 3 = Aperture Priority Mode
CAMERA_AUTO_EXPOSURE = 1

# 1 ate 5000
# Usado somente em modo manual.
CAMERA_EXPOSURE = 100

# 0 = desabilitado
# 1 = camera pode alterar FPS dinamicamente.
# Mantemos 1 por enquanto porque a camera apresentou problema anteriormente quando colocamos 0.
CAMERA_DYNAMIC_FRAMERATE = 1


# ------------------------------------------------------------
# Gain
# ------------------------------------------------------------

# 0 ate 100
CAMERA_GAIN = 10


# ------------------------------------------------------------
# Imagem
# ------------------------------------------------------------

# -64 ate 64
CAMERA_BRIGHTNESS = 0

# 0 ate 64
CAMERA_CONTRAST = 32

# 0 ate 128
CAMERA_SATURATION = 64

# -40 ate 40
CAMERA_HUE = 0

# 0 = manual
# 1 = automatico
CAMERA_HUE_AUTO = 0

# 72 ate 500
CAMERA_GAMMA = 100

# 0 ate 6
CAMERA_SHARPNESS = 3

# 0 ate 2
CAMERA_BACKLIGHT_COMPENSATION = 1


# ------------------------------------------------------------
# White balance
# ------------------------------------------------------------

# 0 = manual
# 1 = automatico
CAMERA_WHITE_BALANCE_AUTO = 1

# 2800 ate 6500 K
# So utilizado quando automatico = 0.
CAMERA_WHITE_BALANCE_TEMPERATURE = 4600


# ------------------------------------------------------------
# Anti-flicker
# ------------------------------------------------------------

# 0 = Disabled
# 1 = 50 Hz
# 2 = 60 Hz
CAMERA_POWER_LINE_FREQUENCY = 2


# ------------------------------------------------------------
# Foco
# ------------------------------------------------------------

# 0 = foco automatico desligado
# 1 = foco automatico continuo
CAMERA_FOCUS_AUTO = 0

# 1 ate 1023
# Usado quando autofocus = 0.
CAMERA_FOCUS = 144


# ============================================================
# FPS REAL
# ============================================================

FPS_MEDICAO_HABILITADA = False

# Exemplo:
# 1 = mede todo segmento fechado
# 2 = mede um a cada dois
# 4 = mede um a cada quatro
MEDIR_FPS_A_CADA_SEGMENTOS = 4

FPS_FFPROBE_TIMEOUT = 30


# ============================================================
# RECUPERACAO DO GRAVADOR
# ============================================================

TENTATIVAS_REINICIO = 3

TEMPO_ENTRE_TENTATIVAS = 2.0

TEMPO_MAX_SEM_ATUALIZAR_VIDEO = 60.0


# ============================================================
# BUZZER
# ============================================================

BUZZER_HABILITADO = True
BUZZER_GPIO = 6


# Sistema rodando normalmente.
BEEP_INTERVALO = 10.0
BEEP_DURACAO = 0.10


# Depois do pouso.
LANDED_BEEP_INTERVALO = 10.0

LANDED_BEEPS_MIN = 2
LANDED_BEEPS_MAX = 8


# ============================================================
# CONTROLE DE ALIMENTACAO
# ============================================================

# True:
# ignora GPIO22 e GPIO17.
#
# False:
# GPIO22 = power hold
# GPIO17 = solicitacao de desligamento
INICIO_COM_BYPASS = False

GPIO_ON = 22
GPIO_OFF = 17

# Tempo que o GPIO_OFF precisa ficar em nivel alto para considerar
# que o usuario realmente quer desligar o Raspberry.
TEMPO_OFF_SEGUNDOS = 3.0


# ============================================================
# ARMAZENAMENTO
# ============================================================

# Liga/desliga APENAS a exclusao automatica.
#
# False:
# nenhum video e apagado automaticamente.
#
# A maquina de estados e os beeps continuam funcionando.
EXCLUSAO_AUTOMATICA_HABILITADA = False


# Mesmo com exclusao automatica desligada,
# pode parar a gravacao para nao zerar o disco.
PARAR_SE_ESPACO_CRITICO = True

# Abaixo desse valor tenta liberar espaco.
ESPACO_MINIMO_GB = 1.0


# Abaixo desse valor para a gravacao caso nao consiga
# recuperar espaco.
ESPACO_CRITICO_GB = 0.5


# Quantos minutos antes do liftoff sao protegidos.
MINUTOS_ANTES_LIFTOFF_PROTEGIDOS = 2


# ============================================================
# BMP280
# ============================================================

BMP280_HABILITADO = True

BMP280_ENDERECO = 0x76

BMP_HZ = 10

BMP_FALHAS_MAX = 20


# ============================================================
# MAQUINA DE ESTADOS
# ============================================================

MAQUINA_ESTADOS_HABILITADA = True


# ------------------------------------------------------------
# LIFTOFF
# ------------------------------------------------------------

ALTITUDE_LIFTOFF_M = 15.0

TEMPO_CONFIRMACAO_LIFTOFF = 1.5


# ------------------------------------------------------------
# LANDED
# ------------------------------------------------------------

TEMPO_LANDED_SEGUNDOS = 30.0

VARIACAO_MAX_LANDED_M = 2.5


# ============================================================
# DADOS
# ============================================================

DADOS_HZ = 5


# ============================================================
# VARIAVEIS GLOBAIS
# ============================================================

buzzer = None

gpio_on = None
gpio_off = None

processo_gravador = None

gravador_atual = GRAVADOR_PRINCIPAL

pasta_gravacao = None

arquivo_log = None
arquivo_dados = None
arquivo_gravador_log = None

bmp280 = None

estado_voo = "IDLE"

tempo_liftoff = None
tempo_landed = None

altitude_base = None

inicio_condicao_liftoff = None

historico_altitude = deque()

falhas_bmp_consecutivas = 0
bmp_indisponivel = False

ultima_pressao = None
ultima_altitude = None

ultimo_bmp = 0.0
ultimo_dados = 0.0

ultimo_beep = 0.0
ultimo_landed_beep = 0.0

inicio_off = None

ultimo_segmento_tamanho = None
ultimo_segmento_tempo = time.monotonic()

buzzer_ocupado = False

encerrando = False

gravacao_bloqueada_por_espaco = False

SISTEMA_PRONTO = False


# FPS
fps_medido = 0.0

ultimo_segmento_analisado = None

fps_analise_em_andamento = False

contador_segmentos_fps = 0


# ============================================================
# LOG
# ============================================================

def log(mensagem, nivel="INFO"):

    texto = (
        f"{datetime.now():%Y-%m-%d %H:%M:%S} | "
        f"{nivel} | {mensagem}"
    )

    print(
        texto,
        flush=True
    )

    if arquivo_log is None:
        return

    try:

        with open(
            arquivo_log,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                texto + "\n"
            )

    except Exception:

        pass


# ============================================================
# LOG DE DADOS
# ============================================================

def iniciar_logs():

    global arquivo_log
    global arquivo_dados

    arquivo_log = (
        pasta_gravacao
        / "sistema.log"
    )

    arquivo_dados = (
        pasta_gravacao
        / "dados.csv"
    )

    try:

        with open(
            arquivo_dados,
            "w",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                "data_hora",
                "estado",
                "pressao_pa",
                "altitude_m",
                "fps_configurado",
                "fps_medido",
                "espaco_livre_gb",
                "gravador"
            ])

    except Exception as e:

        log(
            f"Erro criando dados.csv: {e}",
            "ERROR"
        )


def salvar_dados():

    if arquivo_dados is None:
        return

    try:

        pressao = ""
        altitude = ""

        if ultima_pressao is not None:

            pressao = round(
                ultima_pressao,
                2
            )

        if ultima_altitude is not None:

            altitude = round(
                ultima_altitude,
                2
            )

        with open(
            arquivo_dados,
            "a",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                datetime.now().isoformat(),
                estado_voo,
                pressao,
                altitude,
                FPS,
                round(fps_medido, 2),
                round(espaco_livre_gb(), 3),
                gravador_atual
            ])

    except Exception as e:

        log(
            f"Erro escrevendo dados.csv: {e}",
            "ERROR"
        )


# ============================================================
# CAMERA
# ============================================================

def executar_controle_camera(
    nome,
    valor
):

    try:

        resultado = subprocess.run(
            [
                "v4l2-ctl",
                "-d",
                VIDEO_DEVICE,
                "--set-ctrl",
                f"{nome}={valor}"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )

        if resultado.returncode != 0:

            log(
                f"Camera ctrl {nome}={valor} falhou: "
                f"{resultado.stderr.strip()}",
                "WARNING"
            )

            return False

        return True

    except Exception as e:

        log(
            f"Erro configurando {nome}: {e}",
            "WARNING"
        )

        return False


def configurar_camera():

    if not CAMERA_CONFIG_HABILITADA:

        log(
            "Configuracao da camera desabilitada."
        )

        return


    log(
        "Aplicando configuracoes da camera."
    )


    # --------------------------------------------------------
    # Exposicao
    # --------------------------------------------------------

    executar_controle_camera(
        "auto_exposure",
        CAMERA_AUTO_EXPOSURE
    )

    executar_controle_camera(
        "exposure_dynamic_framerate",
        CAMERA_DYNAMIC_FRAMERATE
    )

    if CAMERA_AUTO_EXPOSURE == 1:

        executar_controle_camera(
            "exposure_time_absolute",
            CAMERA_EXPOSURE
        )


    # --------------------------------------------------------
    # Gain
    # --------------------------------------------------------

    executar_controle_camera(
        "gain",
        CAMERA_GAIN
    )


    # --------------------------------------------------------
    # Imagem
    # --------------------------------------------------------

    executar_controle_camera(
        "brightness",
        CAMERA_BRIGHTNESS
    )

    executar_controle_camera(
        "contrast",
        CAMERA_CONTRAST
    )

    executar_controle_camera(
        "saturation",
        CAMERA_SATURATION
    )

    executar_controle_camera(
        "gamma",
        CAMERA_GAMMA
    )

    executar_controle_camera(
        "sharpness",
        CAMERA_SHARPNESS
    )

    executar_controle_camera(
        "backlight_compensation",
        CAMERA_BACKLIGHT_COMPENSATION
    )


    # --------------------------------------------------------
    # Hue
    # --------------------------------------------------------

    executar_controle_camera(
        "hue_automatic",
        CAMERA_HUE_AUTO
    )

    if CAMERA_HUE_AUTO == 0:

        executar_controle_camera(
            "hue",
            CAMERA_HUE
        )


    # --------------------------------------------------------
    # White balance
    # --------------------------------------------------------

    executar_controle_camera(
        "white_balance_automatic",
        CAMERA_WHITE_BALANCE_AUTO
    )

    if CAMERA_WHITE_BALANCE_AUTO == 0:

        executar_controle_camera(
            "white_balance_temperature",
            CAMERA_WHITE_BALANCE_TEMPERATURE
        )


    # --------------------------------------------------------
    # Anti-flicker
    # --------------------------------------------------------

    executar_controle_camera(
        "power_line_frequency",
        CAMERA_POWER_LINE_FREQUENCY
    )


    # --------------------------------------------------------
    # Foco
    # --------------------------------------------------------

    executar_controle_camera(
        "focus_automatic_continuous",
        CAMERA_FOCUS_AUTO
    )

    if CAMERA_FOCUS_AUTO == 0:

        executar_controle_camera(
            "focus_absolute",
            CAMERA_FOCUS
        )


    log(
        "Configuracao da camera finalizada."
    )


# ============================================================
# BUZZER
# ============================================================

def iniciar_buzzer():

    global buzzer

    if not BUZZER_HABILITADO:
        return

    try:

        buzzer = Buzzer(
            BUZZER_GPIO,
            active_high=False
        )

        buzzer.off()

        log(
            "Buzzer iniciado."
        )

    except Exception as e:

        buzzer = None

        log(
            f"Falha no buzzer: {e}",
            "ERROR"
        )


def executar_beeps(
    quantidade,
    duracao=0.12,
    intervalo=0.12
):

    global buzzer_ocupado

    if not BUZZER_HABILITADO:
        return

    if buzzer is None:
        return

    if buzzer_ocupado:
        return

    buzzer_ocupado = True

    try:

        for _ in range(
            quantidade
        ):

            buzzer.on()

            time.sleep(
                duracao
            )

            buzzer.off()

            time.sleep(
                intervalo
            )

    except Exception as e:

        log(
            f"Erro usando buzzer: {e}",
            "ERROR"
        )

    finally:

        try:

            buzzer.off()

        except Exception:

            pass

        buzzer_ocupado = False


def beeps_async(
    quantidade,
    duracao=0.12,
    intervalo=0.12
):

    thread = threading.Thread(
        target=executar_beeps,
        args=(
            quantidade,
            duracao,
            intervalo
        ),
        daemon=True
    )

    thread.start()


# 2 beeps:
# Python iniciou.
def beep_sistema_iniciado():

    executar_beeps(
        2,
        0.15,
        0.15
    )


# 3 beeps:
# Gravador iniciou.
def beep_gravacao_iniciada():

    executar_beeps(
        1,
        1.0,
        0.50
    )


def beep_fim():

    executar_beeps(
        3,
        0.15,
        0.15
    )


def beep_erro():

    # Antes da primeira gravacao funcionar,
    # erros aparecem apenas no log.
    if not SISTEMA_PRONTO:
        return

    beeps_async(
        5,
        0.08,
        0.08
    )


def atualizar_beep_normal():

    global ultimo_beep

    if not SISTEMA_PRONTO:
        return

    if estado_voo == "LANDED":
        return

    agora = time.monotonic()

    if (
        agora - ultimo_beep
        < BEEP_INTERVALO
    ):

        return

    beeps_async(
        1,
        BEEP_DURACAO,
        0
    )

    ultimo_beep = agora


def atualizar_beep_landed():

    global ultimo_landed_beep

    if not SISTEMA_PRONTO:
        return

    if estado_voo != "LANDED":
        return

    agora = time.monotonic()

    if (
        agora - ultimo_landed_beep
        < LANDED_BEEP_INTERVALO
    ):

        return

    quantidade = random.randint(
        LANDED_BEEPS_MIN,
        LANDED_BEEPS_MAX
    )

    duracao = random.uniform(
        0.08,
        0.20
    )

    intervalo = random.uniform(
        0.08,
        0.25
    )

    beeps_async(
        quantidade,
        duracao,
        intervalo
    )

    ultimo_landed_beep = agora


# ============================================================
# GPIO ON / OFF
# ============================================================

def iniciar_controle_alimentacao():

    global gpio_on
    global gpio_off

    if INICIO_COM_BYPASS:
        return


    # GPIO ON
    try:

        gpio_on = OutputDevice(
            GPIO_ON,
            active_high=True,
            initial_value=True
        )

        gpio_on.on()

    except Exception as e:

        print(
            f"CRITICAL | Falha GPIO ON: {e}",
            flush=True
        )

        sys.exit(1)


    # GPIO OFF
    try:

        gpio_off = DigitalInputDevice(
            GPIO_OFF,
            pull_up=False
        )

    except Exception as e:

        gpio_off = None

        print(
            f"ERROR | Falha GPIO OFF: {e}",
            flush=True
        )


def verificar_off():

    global inicio_off

    if INICIO_COM_BYPASS:
        return

    if gpio_off is None:
        return

    agora = time.monotonic()

    try:

        nivel = gpio_off.value

    except Exception as e:

        log(
            f"Erro lendo GPIO OFF: {e}",
            "ERROR"
        )

        inicio_off = None

        return


    if nivel:

        if inicio_off is None:

            inicio_off = agora

            log(
                "GPIO OFF HIGH."
            )

        elif (
            agora - inicio_off
            >= TEMPO_OFF_SEGUNDOS
        ):

            log(
                "Comando OFF confirmado."
            )

            desligar_raspberry()

    else:

        inicio_off = None


# ============================================================
# SHUTDOWN
# ============================================================

def desligar_raspberry():

    global encerrando

    if encerrando:
        return

    encerrando = True

    log(
        "Iniciando shutdown."
    )

    parar_gravacao()

    beep_fim()

    log(
        "Solicitando shutdown ao Linux."
    )

    try:

        resultado = subprocess.run([
                "sudo",
                "-n",
                "/usr/sbin/shutdown",
                "-h",
                "now"
            ])

        if resultado.returncode != 0:

            log(
                "Comando shutdown retornou erro.",
                "CRITICAL"
            )

            encerrando = False

    except Exception as e:

        log(
            f"Falha executando shutdown: {e}",
            "CRITICAL"
        )

        encerrando = False


# ============================================================
# ARMAZENAMENTO
# ============================================================

def espaco_livre_gb():

    try:

        _, _, livre = shutil.disk_usage(
            PASTA_BASE
        )

        return (
            livre
            / (1024 ** 3)
        )

    except Exception as e:

        log(
            f"Erro consultando disco: {e}",
            "ERROR"
        )

        return 0.0


def listar_segmentos():

    if pasta_gravacao is None:
        return []

    try:

        return sorted(
            pasta_gravacao.glob(
                "video_*.mkv"
            ),
            key=lambda p:
            p.stat().st_mtime
        )

    except Exception as e:

        log(
            f"Erro listando segmentos: {e}",
            "ERROR"
        )

        return []


def segmentos_fechados():

    segmentos = listar_segmentos()

    if len(segmentos) <= 1:
        return []

    # Nunca considera o ultimo arquivo pois esta sendo gravado.
    return segmentos[:-1]


def apagar_segmento(
    arquivo
):

    try:

        tamanho_mb = (
            arquivo.stat().st_size
            / (1024 ** 2)
        )

        arquivo.unlink()

        log(
            f"Video apagado: "
            f"{arquivo.name} "
            f"({tamanho_mb:.1f} MB)"
        )

        return True

    except Exception as e:

        log(
            f"Erro apagando "
            f"{arquivo.name}: {e}",
            "ERROR"
        )

        return False


# ============================================================
# POLITICA DE EXCLUSAO
# ============================================================

def obter_segmentos_apagaveis():

    if not EXCLUSAO_AUTOMATICA_HABILITADA:

        return []


    segmentos = segmentos_fechados()

    if not segmentos:
        return []


    # --------------------------------------------------------
    # IDLE
    # --------------------------------------------------------

    if estado_voo == "IDLE":

        return []


    # --------------------------------------------------------
    # FLIGHT
    # --------------------------------------------------------

    if estado_voo == "FLIGHT":

        if tempo_liftoff is None:
            return []

        inicio_protegido = (
            tempo_liftoff.timestamp()
            - MINUTOS_ANTES_LIFTOFF_PROTEGIDOS
            * 60
        )

        apagaveis = []

        for arquivo in segmentos:

            try:

                tempo = (
                    arquivo.stat().st_mtime
                )

                if tempo < inicio_protegido:

                    apagaveis.append(
                        arquivo
                    )

            except Exception:

                pass

        return apagaveis


    # --------------------------------------------------------
    # LANDED
    # --------------------------------------------------------

    if estado_voo == "LANDED":

        if (
            tempo_liftoff is None
            or tempo_landed is None
        ):

            return []

        inicio_protegido = (
            tempo_liftoff.timestamp()
            - MINUTOS_ANTES_LIFTOFF_PROTEGIDOS
            * 60
        )

        fim_protegido = (
            tempo_landed.timestamp()
        )

        apagaveis = []

        for arquivo in segmentos:

            try:

                tempo = (
                    arquivo.stat().st_mtime
                )

                # Antes da janela pre-liftoff.
                if tempo < inicio_protegido:

                    apagaveis.append(
                        arquivo
                    )

                # Depois do pouso.
                elif tempo > fim_protegido:

                    apagaveis.append(
                        arquivo
                    )

            except Exception:

                pass

        return apagaveis


    return []


# ============================================================
# BLOQUEIO POR ESPACO
# ============================================================

def bloquear_gravacao_por_espaco():

    global gravacao_bloqueada_por_espaco

    if gravacao_bloqueada_por_espaco:
        return

    gravacao_bloqueada_por_espaco = True

    log(
        "Gravacao bloqueada por falta de espaco.",
        "CRITICAL"
    )

    parar_gravacao()

    beep_erro()


def verificar_desbloqueio_espaco():

    global gravacao_bloqueada_por_espaco

    if not gravacao_bloqueada_por_espaco:
        return

    if (
        espaco_livre_gb()
        >= ESPACO_MINIMO_GB
    ):

        gravacao_bloqueada_por_espaco = False

        log(
            "Espaco recuperado. "
            "Gravacao liberada."
        )


def gerenciar_armazenamento():

    livre = espaco_livre_gb()


    # Tudo normal.
    if livre >= ESPACO_MINIMO_GB:

        verificar_desbloqueio_espaco()

        return


    # --------------------------------------------------------
    # Exclusao automatica
    # --------------------------------------------------------

    if EXCLUSAO_AUTOMATICA_HABILITADA:

        candidatos = (
            obter_segmentos_apagaveis()
        )

        for arquivo in candidatos:

            if (
                espaco_livre_gb()
                >= ESPACO_MINIMO_GB
            ):

                break

            apagar_segmento(
                arquivo
            )


    livre = espaco_livre_gb()


    # Recuperou espaco.
    if livre >= ESPACO_MINIMO_GB:

        verificar_desbloqueio_espaco()

        return


    # --------------------------------------------------------
    # Espaco critico
    # --------------------------------------------------------

    if (
        PARAR_SE_ESPACO_CRITICO
        and
        livre <= ESPACO_CRITICO_GB
    ):

        log(
            "Espaco critico. "
            "Parando gravacao.",
            "CRITICAL"
        )

        bloquear_gravacao_por_espaco()


# ============================================================
# BMP280
# ============================================================

def iniciar_bmp280():

    global bmp280
    global bmp_indisponivel
    global falhas_bmp_consecutivas

    if not BMP280_HABILITADO:

        log(
            "BMP280 desabilitado."
        )

        return

    try:

        import board
        import adafruit_bmp280

        i2c = board.I2C()

        bmp280 = (
            adafruit_bmp280
            .Adafruit_BMP280_I2C(
                i2c,
                address=BMP280_ENDERECO
            )
        )

        bmp280.sea_level_pressure = (
            1013.25
        )

        bmp_indisponivel = False

        falhas_bmp_consecutivas = 0

        log(
            "BMP280 iniciado."
        )

    except Exception as e:

        bmp280 = None

        bmp_indisponivel = True

        log(
            f"Falha iniciando BMP280: {e}",
            "ERROR"
        )

        beep_erro()


def ler_bmp280():

    global falhas_bmp_consecutivas
    global bmp_indisponivel

    if not BMP280_HABILITADO:
        return None

    if bmp_indisponivel:
        return None

    if bmp280 is None:
        return None

    try:

        pressao = (
            bmp280.pressure
            * 100.0
        )

        altitude = (
            bmp280.altitude
        )

        falhas_bmp_consecutivas = 0

        return (
            pressao,
            altitude
        )

    except Exception as e:

        falhas_bmp_consecutivas += 1

        log(
            f"Erro BMP280 "
            f"{falhas_bmp_consecutivas}/"
            f"{BMP_FALHAS_MAX}: {e}",
            "WARNING"
        )

        if (
            falhas_bmp_consecutivas
            >= BMP_FALHAS_MAX
        ):

            bmp_indisponivel = True

            log(
                "BMP280 considerado indisponivel.",
                "ERROR"
            )

            beep_erro()

        return None


# ============================================================
# MAQUINA DE ESTADOS
# ============================================================

def atualizar_maquina_estados(
    altitude
):

    global estado_voo
    global altitude_base
    global inicio_condicao_liftoff
    global tempo_liftoff
    global tempo_landed

    if not MAQUINA_ESTADOS_HABILITADA:
        return

    if not BMP280_HABILITADO:
        return

    if bmp_indisponivel:
        return

    agora = time.monotonic()


    # ========================================================
    # IDLE
    # ========================================================

    if estado_voo == "IDLE":

        if altitude_base is None:

            altitude_base = altitude

            log(
                f"Altitude base: "
                f"{altitude_base:.2f} m"
            )

            return


        altitude_base = (
            0.995 * altitude_base
            + 0.005 * altitude
        )


        delta_altitude = (
            altitude
            - altitude_base
        )


        if (
            delta_altitude
            >= ALTITUDE_LIFTOFF_M
        ):

            if (
                inicio_condicao_liftoff
                is None
            ):

                inicio_condicao_liftoff = agora

            elif (
                agora
                - inicio_condicao_liftoff
                >= TEMPO_CONFIRMACAO_LIFTOFF
            ):

                estado_voo = "FLIGHT"

                tempo_liftoff = (
                    datetime.now()
                )

                historico_altitude.clear()

                log(
                    f"LIFTOFF | "
                    f"Altitude={altitude:.2f} m",
                    "EVENT"
                )

                beeps_async(
                    3
                )

        else:

            inicio_condicao_liftoff = None


        return


    # ========================================================
    # FLIGHT
    # ========================================================

    if estado_voo == "FLIGHT":

        historico_altitude.append(
            (
                agora,
                altitude
            )
        )


        while (
            historico_altitude
            and
            agora
            - historico_altitude[0][0]
            > TEMPO_LANDED_SEGUNDOS
        ):

            historico_altitude.popleft()


        if (
            len(historico_altitude)
            < 2
        ):

            return


        duracao = (
            historico_altitude[-1][0]
            - historico_altitude[0][0]
        )


        if (
            duracao
            < TEMPO_LANDED_SEGUNDOS
        ):

            return


        altitudes = [
            valor
            for _, valor
            in historico_altitude
        ]


        maior = max(
            altitudes
        )

        menor = min(
            altitudes
        )

        variacao = (
            maior
            - menor
        )


        if (
            variacao
            <= VARIACAO_MAX_LANDED_M
        ):

            estado_voo = "LANDED"

            tempo_landed = (
                datetime.now()
            )

            log(
                f"LANDED | "
                f"Altitude={altitude:.2f} m | "
                f"Variacao={variacao:.2f} m",
                "EVENT"
            )

            beeps_async(
                6
            )

        return


    # ========================================================
    # LANDED
    # ========================================================

    if estado_voo == "LANDED":

        return


# ============================================================
# GSTREAMER
# ============================================================

def montar_comando_gstreamer():

    arquivo = str(
        pasta_gravacao
        / "video_%05d.mkv"
    )

    return [

        "gst-launch-1.0",
        "-e",

        "splitmuxsink",
        "name=mux",

        f"location={arquivo}",

        (
            f"max-size-time="
            f"{SEGMENTO_SEGUNDOS * 1_000_000_000}"
        ),

        "muxer-factory=matroskamux",


        # VIDEO
        "v4l2src",
        f"device={VIDEO_DEVICE}",

        "!",

        (
            f"image/jpeg,"
            f"width={WIDTH},"
            f"height={HEIGHT},"
            f"framerate={FPS}/1"
        ),

        "!",
        "jpegparse",

        "!",
        "queue",

        "!",
        "mux.video",


        # AUDIO
        "alsasrc",
        f"device={AUDIO_DEVICE}",

        "buffer-time=500000",
        "latency-time=20000",
        "do-timestamp=true",

        "!",

        (
            "audio/x-raw,"
            "format=S16LE,"
            "rate=48000,"
            "channels=2"
        ),

        "!",
        "audioconvert",

        "!",
        "audioresample",

        "!",
        "avenc_aac",
        "bitrate=128000",

        "!",
        "aacparse",

        "!",
        "queue",

        "!",
        "mux.audio_0"
    ]


# ============================================================
# FFMPEG
# ============================================================

def montar_comando_ffmpeg():

    arquivo = str(
        pasta_gravacao
        / "video_%05d.mkv"
    )

    return [

        "ffmpeg",

        "-hide_banner",
        "-loglevel",
        "warning",


        # VIDEO
        "-f",
        "v4l2",

        "-input_format",
        "mjpeg",

        "-video_size",
        f"{WIDTH}x{HEIGHT}",

        "-framerate",
        str(FPS),

        "-i",
        VIDEO_DEVICE,


        # AUDIO
        "-f",
        "alsa",

        "-i",
        AUDIO_DEVICE,


        # VIDEO SEM REENCODE
        "-c:v",
        "copy",


        # AAC
        "-c:a",
        "aac",

        "-b:a",
        AUDIO_BITRATE,


        # SEGMENTACAO
        "-f",
        "segment",

        "-segment_time",
        str(SEGMENTO_SEGUNDOS),

        "-reset_timestamps",
        "1",

        arquivo
    ]


# ============================================================
# GRAVADOR
# ============================================================

def montar_comando_gravador():

    if gravador_atual == "gstreamer":

        return (
            montar_comando_gstreamer()
        )

    if gravador_atual == "ffmpeg":

        return (
            montar_comando_ffmpeg()
        )

    raise ValueError(
        f"Gravador invalido: "
        f"{gravador_atual}"
    )


def iniciar_gravacao():

    global processo_gravador
    global arquivo_gravador_log

    if gravacao_bloqueada_por_espaco:

        log(
            "Gravacao bloqueada por armazenamento.",
            "WARNING"
        )

        return False


    try:

        comando = (
            montar_comando_gravador()
        )

    except Exception as e:

        log(
            f"Erro montando gravador: {e}",
            "ERROR"
        )

        return False


    log(
        f"Iniciando {gravador_atual}."
    )


    try:

        arquivo_gravador_log = open(
            pasta_gravacao
            / "gravador.log",
            "a",
            encoding="utf-8"
        )


        processo_gravador = (
            subprocess.Popen(
                comando,
                stdout=arquivo_gravador_log,
                stderr=arquivo_gravador_log
            )
        )


        time.sleep(
            1
        )


        if (
            processo_gravador.poll()
            is not None
        ):

            log(
                f"{gravador_atual} falhou ao iniciar.",
                "ERROR"
            )

            processo_gravador = None

            return False


        log(
            f"Gravacao iniciada com "
            f"{gravador_atual}."
        )

        return True


    except Exception as e:

        processo_gravador = None

        log(
            f"Erro iniciando "
            f"{gravador_atual}: {e}",
            "ERROR"
        )

        return False


def gravacao_ativa():

    return (
        processo_gravador
        is not None
        and
        processo_gravador.poll()
        is None
    )


def parar_gravacao():

    global processo_gravador
    global arquivo_gravador_log

    if processo_gravador is None:
        return


    try:

        if (
            processo_gravador.poll()
            is None
        ):

            processo_gravador.send_signal(
                signal.SIGINT
            )


            try:

                processo_gravador.wait(
                    timeout=8
                )

            except subprocess.TimeoutExpired:

                processo_gravador.terminate()


                try:

                    processo_gravador.wait(
                        timeout=3
                    )

                except subprocess.TimeoutExpired:

                    processo_gravador.kill()


    except Exception as e:

        log(
            f"Erro encerrando gravador: {e}",
            "ERROR"
        )


    processo_gravador = None


    if arquivo_gravador_log is not None:

        try:

            arquivo_gravador_log.close()

        except Exception:

            pass

        arquivo_gravador_log = None


def trocar_gravador():

    global gravador_atual

    if GRAVADOR_FALLBACK is None:
        return False

    if (
        gravador_atual
        == GRAVADOR_FALLBACK
    ):

        return False

    log(
        f"Trocando gravador: "
        f"{gravador_atual} -> "
        f"{GRAVADOR_FALLBACK}",
        "WARNING"
    )

    gravador_atual = (
        GRAVADOR_FALLBACK
    )

    return True


def tentar_recuperar_gravacao():

    if gravacao_bloqueada_por_espaco:
        return False


    beep_erro()


    for tentativa in range(
        1,
        TENTATIVAS_REINICIO + 1
    ):

        log(
            f"Recuperacao "
            f"{tentativa}/"
            f"{TENTATIVAS_REINICIO}",
            "WARNING"
        )


        parar_gravacao()


        time.sleep(
            TEMPO_ENTRE_TENTATIVAS
        )


        configurar_camera()


        if iniciar_gravacao():

            log(
                "Gravador recuperado."
            )

            return True


    if trocar_gravador():

        log(
            "Tentando gravador fallback.",
            "WARNING"
        )

        configurar_camera()

        if iniciar_gravacao():

            log(
                "Fallback funcionando."
            )

            return True


    log(
        "Falha total da gravacao.",
        "CRITICAL"
    )

    return False


# ============================================================
# FPS REAL
# ============================================================

def medir_fps_segmento(
    arquivo
):

    try:

        comando = [

            "ffprobe",

            "-v",
            "error",

            "-select_streams",
            "v:0",

            "-count_packets",

            "-show_entries",
            "stream=nb_read_packets:format=duration",

            "-of",
            "default=noprint_wrappers=1",

            str(
                arquivo
            )
        ]


        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=FPS_FFPROBE_TIMEOUT
        )


        if resultado.returncode != 0:
            return None


        quantidade = None
        duracao = None


        for linha in (
            resultado.stdout.splitlines()
        ):

            if linha.startswith(
                "nb_read_packets="
            ):

                valor = (
                    linha.split(
                        "=",
                        1
                    )[1]
                )

                if valor != "N/A":

                    quantidade = int(
                        valor
                    )


            elif linha.startswith(
                "duration="
            ):

                valor = (
                    linha.split(
                        "=",
                        1
                    )[1]
                )

                if valor != "N/A":

                    duracao = float(
                        valor
                    )


        if (
            quantidade is None
            or duracao is None
            or duracao <= 0
        ):

            return None


        return (
            quantidade
            / duracao
        )


    except subprocess.TimeoutExpired:

        log(
            "ffprobe excedeu o tempo limite.",
            "WARNING"
        )

        return None


    except Exception as e:

        log(
            f"Erro medindo FPS: {e}",
            "WARNING"
        )

        return None


def analisar_fps_async(
    arquivo
):

    global fps_medido
    global fps_analise_em_andamento

    try:

        fps = medir_fps_segmento(
            arquivo
        )

        if fps is not None:

            fps_medido = fps

            log(
                f"FPS medido: "
                f"{fps_medido:.2f}"
            )

    finally:

        fps_analise_em_andamento = False


def atualizar_fps_medido():

    global ultimo_segmento_analisado
    global fps_analise_em_andamento
    global contador_segmentos_fps

    if not FPS_MEDICAO_HABILITADA:
        return

    if fps_analise_em_andamento:
        return


    segmentos = (
        segmentos_fechados()
    )


    if not segmentos:
        return


    ultimo_fechado = (
        segmentos[-1]
    )


    if (
        ultimo_fechado
        == ultimo_segmento_analisado
    ):

        return


    ultimo_segmento_analisado = (
        ultimo_fechado
    )


    contador_segmentos_fps += 1


    if (
        contador_segmentos_fps
        < MEDIR_FPS_A_CADA_SEGMENTOS
    ):

        return


    contador_segmentos_fps = 0


    fps_analise_em_andamento = True


    thread = threading.Thread(
        target=analisar_fps_async,
        args=(
            ultimo_fechado,
        ),
        daemon=True
    )

    thread.start()


# ============================================================
# WATCHDOG DE VIDEO
# ============================================================

def verificar_segmentos():

    global ultimo_segmento_tamanho
    global ultimo_segmento_tempo

    if gravacao_bloqueada_por_espaco:
        return

    if not gravacao_ativa():
        return


    segmentos = (
        listar_segmentos()
    )


    if not segmentos:
        return


    ultimo = segmentos[-1]


    try:

        tamanho = (
            ultimo.stat().st_size
        )

    except Exception:

        return


    agora = time.monotonic()


    if (
        tamanho
        != ultimo_segmento_tamanho
    ):

        ultimo_segmento_tamanho = (
            tamanho
        )

        ultimo_segmento_tempo = (
            agora
        )

        return


    if (
        agora
        - ultimo_segmento_tempo
        > TEMPO_MAX_SEM_ATUALIZAR_VIDEO
    ):

        log(
            "Video parou de crescer.",
            "ERROR"
        )

        ultimo_segmento_tempo = agora

        if not tentar_recuperar_gravacao():

            sys.exit(
                1
            )


# ============================================================
# PASTA
# ============================================================

def criar_pasta_gravacao():

    global pasta_gravacao

    data = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    pasta_gravacao = (
        PASTA_BASE
        / data
    )

    pasta_gravacao.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# ENCERRAMENTO
# ============================================================

def encerrar(
    sig=None,
    frame=None
):

    global encerrando

    if encerrando:
        return

    encerrando = True


    log(
        "Encerrando sistema."
    )


    parar_gravacao()


    beep_fim()


    if buzzer is not None:

        try:

            buzzer.off()

            buzzer.close()

        except Exception:

            pass


    if gpio_off is not None:

        try:

            gpio_off.close()

        except Exception:

            pass


    log(
        "Sistema encerrado."
    )


    sys.exit(
        0
    )


# ============================================================
# SIGNALS
# ============================================================

def configurar_signals():

    signal.signal(
        signal.SIGINT,
        encerrar
    )

    signal.signal(
        signal.SIGTERM,
        encerrar
    )


# ============================================================
# MAIN
# ============================================================

def main():

    global ultimo_bmp
    global ultimo_dados

    global ultima_pressao
    global ultima_altitude

    global SISTEMA_PRONTO


    # --------------------------------------------------------
    # Estrutura minima
    # --------------------------------------------------------

    PASTA_BASE.mkdir(
        parents=True,
        exist_ok=True
    )


    # Power hold primeiro.
    iniciar_controle_alimentacao()


    criar_pasta_gravacao()

    iniciar_logs()

    configurar_signals()

    iniciar_buzzer()


    # --------------------------------------------------------
    # Primeiro aviso:
    # Python iniciou.
    # --------------------------------------------------------

    beep_sistema_iniciado()


    log(
        f"Espaco livre: "
        f"{espaco_livre_gb():.2f} GB"
    )

    log(
        f"Gravador principal: "
        f"{gravador_atual}"
    )

    log(
        f"Resolucao: "
        f"{WIDTH}x{HEIGHT}"
    )

    log(
        f"FPS solicitado: "
        f"{FPS}"
    )


    # --------------------------------------------------------
    # Camera
    # --------------------------------------------------------

    configurar_camera()


    # --------------------------------------------------------
    # BMP
    # --------------------------------------------------------

    iniciar_bmp280()


    # --------------------------------------------------------
    # Gravador
    # --------------------------------------------------------

    if not iniciar_gravacao():

        if not tentar_recuperar_gravacao():

            log(
                "Nenhum gravador iniciou.",
                "CRITICAL"
            )

            sys.exit(
                1
            )


    # --------------------------------------------------------
    # A partir daqui o sistema esta oficialmente pronto.
    # --------------------------------------------------------

    SISTEMA_PRONTO = True


    # Segundo aviso:
    # gravacao realmente iniciou.
    beep_gravacao_iniciada()


    log(
        "Sistema pronto e gravando.",
        "EVENT"
    )


    # ========================================================
    # LOOP PRINCIPAL
    # ========================================================

    while True:

        agora = time.monotonic()


        # ----------------------------------------------------
        # OFF
        # ----------------------------------------------------

        verificar_off()


        # ----------------------------------------------------
        # Buzzer
        # ----------------------------------------------------

        atualizar_beep_normal()

        atualizar_beep_landed()


        # ----------------------------------------------------
        # BMP
        # ----------------------------------------------------

        if (
            BMP280_HABILITADO
            and
            not bmp_indisponivel
            and
            agora - ultimo_bmp
            >= (1.0 / BMP_HZ)
        ):

            ultimo_bmp = agora


            leitura = (
                ler_bmp280()
            )


            if leitura is not None:

                (
                    ultima_pressao,
                    ultima_altitude
                ) = leitura


                atualizar_maquina_estados(
                    ultima_altitude
                )


        # ----------------------------------------------------
        # FPS
        # ----------------------------------------------------

        atualizar_fps_medido()


        # ----------------------------------------------------
        # CSV
        # ----------------------------------------------------

        if (
            agora - ultimo_dados
            >= (1.0 / DADOS_HZ)
        ):

            ultimo_dados = agora

            salvar_dados()


        # ----------------------------------------------------
        # Armazenamento
        # ----------------------------------------------------

        gerenciar_armazenamento()


        # ----------------------------------------------------
        # Gravador
        # ----------------------------------------------------

        if not gravacao_bloqueada_por_espaco:

            if not gravacao_ativa():

                log(
                    "Gravador morreu.",
                    "ERROR"
                )


                if not tentar_recuperar_gravacao():

                    log(
                        "Recuperacao impossivel.",
                        "CRITICAL"
                    )

                    sys.exit(
                        1
                    )


            else:

                verificar_segmentos()


        # ----------------------------------------------------
        # Loop
        # ----------------------------------------------------

        time.sleep(
            0.02
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
