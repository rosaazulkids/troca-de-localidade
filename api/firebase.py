import requests
import json


class Firebase:
    def __init__(self):
        self.url = "https://rosa-azul-kids-teste-default-rtdb.firebaseio.com/"

    def post_item(self, caminho, dados):
        requisicao = requests.post(url=self.url + f'/{caminho}/.json', data=json.dumps(dados))
        print('Adicionado', dados, requisicao, requisicao.text)
        return requisicao.json()

    def patch_item(self, caminho, dados):
        requisicao = requests.patch(url=self.url + f'/{caminho}/.json', data=json.dumps(dados))
        print('Editado', dados, requisicao, requisicao.text)
        return requisicao.json()

    def delete_item(self, caminho, id_item):
        requisicao = requests.delete(url=self.url + f'/{caminho}/{id_item}/.json')
        print('Deletado', id_item, requisicao, requisicao.text)
        return requisicao.json()

    def get_item(self, caminho, id_item):
        requisicao = requests.get(url=self.url + f'/{caminho}/{id_item}/.json')
        return requisicao.json()
