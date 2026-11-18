import subprocess
from pathlib import Path


# ============================================================
# CONFIGURACOES
# ============================================================

PASTA = Path(__file__).resolve().parent

PADRAO_VIDEO = "video_*.mkv"

ARQUIVO_SAIDA = PASTA / "video_completo.mkv"

ARQUIVO_LISTA = PASTA / "lista_videos.txt"


# ============================================================
# ENCONTRAR VIDEOS
# ============================================================

videos = sorted(
    PASTA.glob(PADRAO_VIDEO)
)

if not videos:

    print("Nenhum video encontrado.")
    input("Enter para sair...")
    raise SystemExit(1)


print(f"Foram encontrados {len(videos)} videos:")

for video in videos:

    print(f"  {video.name}")


# ============================================================
# CRIAR LISTA PARA O FFMPEG
# ============================================================

with open(
    ARQUIVO_LISTA,
    "w",
    encoding="utf-8"
) as arquivo:

    for video in videos:

        caminho = str(video.resolve())

        # FFmpeg concat usa aspas simples.
        caminho = caminho.replace(
            "'",
            "'\\''"
        )

        arquivo.write(
            f"file '{caminho}'\n"
        )


# ============================================================
# JUNTAR
# ============================================================

comando = [
    "ffmpeg",

    "-hide_banner",

    "-f",
    "concat",

    "-safe",
    "0",

    "-i",
    str(ARQUIVO_LISTA),

    # Nao recodifica.
    "-c",
    "copy",

    "-y",

    str(ARQUIVO_SAIDA)
]


print()
print("Juntando videos...")
print()


try:

    resultado = subprocess.run(
        comando
    )


except FileNotFoundError:

    print()
    print("ERRO: FFmpeg nao foi encontrado.")
    print("Instale o FFmpeg ou coloque-o no PATH do Windows.")

    input("Enter para sair...")

    raise SystemExit(1)


# ============================================================
# RESULTADO
# ============================================================

if resultado.returncode == 0:

    print()
    print("Concluido!")
    print()
    print(f"Arquivo: {ARQUIVO_SAIDA}")

else:

    print()
    print("FFmpeg terminou com erro.")


input("\nEnter para sair...")