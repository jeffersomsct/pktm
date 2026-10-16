import requests

BASE_URL = "https://parallelum.com.br/fipe/api/v1"

def modelos_por_ano(tipo, marca_codigo, ano_desejado):
    resposta = requests.get(f"{BASE_URL}/{tipo}/marcas/{marca_codigo}/modelos").json()
    print("Resposta da API:", resposta)  # Adicione esta linha para depuração
    if "modelos" not in resposta:
        raise ValueError(f"Resposta inesperada da API: {resposta}")
    modelos = resposta["modelos"]
    modelos_com_ano = []

    for modelo in modelos:
        anos = requests.get(f"{BASE_URL}/{tipo}/marcas/{marca_codigo}/modelos/{modelo['codigo']}/anos").json()
        for ano in anos:
            if isinstance(ano, dict) and "nome" in ano and str(ano_desejado) in ano["nome"]:
                modelos_com_ano.append({
                    "codigo": modelo["codigo"],
                    "nome": modelo["nome"],
                    "ano": ano["nome"],
                    "codigo_ano": ano["codigo"]
                })

    return modelos_com_ano

# Exemplo de uso: buscar todos os modelos FIAT disponíveis no ano 2003
if __name__ == "__main__":
    tipo = "carros"
    marca_codigo = 21  # Fiat
    ano_desejado = 2003

    resultados = modelos_por_ano(tipo, marca_codigo, ano_desejado)

    if resultados:
        print(f"Modelos FIAT disponíveis no ano {ano_desejado}:\n")
        for r in resultados:
            print(f"- {r['nome']} ({r['ano']}) | código modelo: {r['codigo']} | código ano: {r['codigo_ano']}")
    else:
        print(f"Nenhum modelo encontrado para {ano_desejado}")
