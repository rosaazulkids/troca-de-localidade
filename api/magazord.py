import requests
import json as js


class Magazord:
    def __init__(self, user: str, password: str, url: str):
        self.user = user
        self.password = password
        self.url = url

    # Retorna todas as informações do produto
    def get_produto(self, codigo_produto: str, codigo_derivacao: str):
        url = self.url + "v2/site/produto/" + codigo_produto + "/derivacao/" + codigo_derivacao

        resp = requests.get(url, data={}, auth=(self.user, self.password))

        return js.loads(resp.text)

    # Retorna uma lista com todas as localizações do produto informado
    def get_produto_localidades(self, codigo_produto: str):
        url = self.url + "v2/estoqueLocalizacao/produto/" + codigo_produto

        resp = requests.get(url, data={}, auth=(self.user, self.password))

        dic = js.loads(resp.text)

        all_locs = []

        if 'data' in dic:
            for loc in dic['data']:
                all_locs.append(loc['localizacao']['descricao'])

        return all_locs

    # Retorna os itens na localização do depósito fornecidos
    def get_localidade(self, deposito: int, codigo_localizacao: str):
        url = self.url + f"v2/estoqueLocalizacao/deposito/{deposito}/localizacao/{codigo_localizacao}"

        resp = requests.get(url, auth=(self.user, self.password))

        dic = js.loads(resp.text)

        if dic['status'] == 'error':
            return False

        retorno = {}
        if 'data' in dic:
            for item in dic['data']:
                sku = item['estoque']['produtoDerivacao']['codigo']
                estoque = item['quantidadeConfigurada']
                reservado = item['quantidadeReservada']
                retorno[sku] = {}
                retorno[sku]['configurado'] = estoque
                retorno[sku]['reservado'] = reservado

        return retorno

    # Vincula a localidade ao sku
    def post_vincular_localidade(self, produto_derivacao: str, deposito: int, localidade: str):
        url = self.url + "v2/estoqueLocalizacao/"

        json = {
            "produtoDerivacao": str(produto_derivacao),
            "deposito": int(deposito),
            "localizacao": str(localidade)
        }

        response = requests.post(url, json=json, auth=(self.user, self.password))

        return js.loads(response.text)

    # Altera as quantidades da localidade
    def put_produto_localidade(self, produto_derivacao: str, deposito: int, localidade: str,
                               quantidade_reservada: int = 0, quantidade_configurada: int = 0):
        url = self.url + "v2/estoqueLocalizacao/"

        json = {
            "produtoDerivacao": str(produto_derivacao),
            "deposito": int(deposito),
            "localizacao": str(localidade),
            "quantidadeReservada": int(quantidade_reservada),  # Opcional
            "quantidadeConfigurada": int(quantidade_configurada)  # Opcional
        }

        response = requests.put(url, json=json, auth=(self.user, self.password))

        return js.loads(response.text)
