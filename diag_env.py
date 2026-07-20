import os

CAMINHO = os.path.join(os.getcwd(), ".env")
print(f"Procurando em: {CAMINHO}")
print(f"Arquivo existe? {os.path.exists(CAMINHO)}")
print("-" * 50)

if os.path.exists(CAMINHO):
    # 1. Mostra os bytes crus do início do arquivo (revela BOM e caracteres ocultos)
    with open(CAMINHO, "rb") as f:
        primeiros_bytes = f.read(40)
    print("Primeiros bytes (hex):", primeiros_bytes.hex())
    print("Primeiros bytes (repr):", repr(primeiros_bytes))
    print("-" * 50)

    # 2. Mostra cada linha do arquivo, char a char, revelando espaços/BOM/aspas ocultas
    with open(CAMINHO, "r", encoding="utf-8-sig") as f:
        linhas = f.readlines()
    print(f"Total de linhas: {len(linhas)}")
    for i, linha in enumerate(linhas):
        print(f"Linha {i+1} (repr): {repr(linha)}")
    print("-" * 50)

    # 3. Tenta carregar de verdade com python-dotenv e mostra o resultado
    from dotenv import load_dotenv
    resultado = load_dotenv(dotenv_path=CAMINHO, encoding="utf-8-sig", override=True)
    print(f"load_dotenv() retornou: {resultado}")
    print(f"SUPABASE_URL lido: {repr(os.getenv('SUPABASE_URL'))}")
    print(f"SUPABASE_KEY lido: {repr(os.getenv('SUPABASE_KEY'))}")
else:
    print("Arquivo .env não encontrado nesse caminho. Rode este script de dentro da pasta do projeto (Prontu).")