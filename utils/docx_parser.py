import docx
import re

def extrair_dados_docx(caminho_arquivo):
    """Lê o arquivo DOCX da Dra. Laura e extrai os campos-chave usando Expressões Regulares."""
    try:
        doc = docx.Document(caminho_arquivo)
        # Junta todo o texto das linhas do documento quebrando por linha
        texto_completo = "\n".join([paragrafo.text for paragrafo in doc.paragraphs])
        
        # Dicionário padrão com dados limpos
        dados = {
            "nome": "",
            "endereco": "",
            "telefone": "",
            "nascimento": "01/01/1980",
            "convenio": "PARTICULAR",
            "qp": ""
        }
        
        # Regex para capturar os dados baseados no padrão do documento da Dra. Laura
        match_nome = re.search(r"Nome:\s*(.*)", texto_completo, re.IGNORECASE)
        match_end = re.search(r"Endereço:\s*(.*)", texto_completo, re.IGNORECASE)
        match_fone = re.search(r"Fone:\s*(.*)", texto_completo, re.IGNORECASE)
        match_nasc = re.search(r"Data Nasc:\s*([\d/]+)", texto_completo, re.IGNORECASE)
        match_conv = re.search(r"Convênio:\s*(.*)", texto_completo, re.IGNORECASE)
        match_qp = re.search(r"QP\s*:\s*(.*)", texto_completo, re.IGNORECASE)
        
        if match_nome: dados["nome"] = match_nome.group(1).strip()
        if match_end: dados["endereco"] = match_end.group(1).strip()
        if match_fone: dados["telefone"] = "".join(filter(str.isdigit, match_fone.group(1))) # Apenas números
        if match_nasc: dados["nascimento"] = match_nasc.group(1).strip()
        if match_conv: dados["convenio"] = match_conv.group(1).strip()
        if match_qp: dados["qp"] = match_qp.group(1).replace(",,", "").strip()
            
        return dados
    except Exception as e:
        print(f"Erro ao ler o arquivo Word: {e}")
        return None