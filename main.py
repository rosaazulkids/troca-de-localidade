from flask import Flask, render_template, redirect, request
from api.magazord import Magazord
from api.firebase import Firebase
from datetime import datetime


app = Flask(__name__)


# INICIALIZAÇÃO API's - MAGAZORD
mz_rosa_azul = Magazord(
    user="f84469d2014ef65c47146ccffa8d2093f79393da5c34b2dd9efbda6fdaab3883",
    password="123456789",
    url="https://rosaazul.painel.magazord.com.br/api/"
)
mz_use_force = Magazord(
    user="abc13ad402e669fb7691fcf5a867cba5f12fced671694e5fe1b83d302c343ec8",
    password="123456789",
    url="https://useforce.painel.magazord.com.br/api/"
)
magazord = {'rosa-azul': mz_rosa_azul, 'use-force': mz_use_force}


# INICIALIZAÇÃO API's - FIREBASE
firebase = Firebase()


@app.route("/")
def homepage():
    print('Mandar para tela de login ou direto para a troca de localidade')
    return redirect('/troca-de-localidade')


# ROTAS DE VISUALIZAÇÃO
@app.route("/login")
def login():
    return 'Tela de login'


@app.route("/troca-de-localidade")
def troca_de_localidade():
    lista = firebase.get_item(caminho='', id_item='Troca-Localidade')
    return render_template("troca_de_localidade.html", lista_troca_localidade=reversed(lista))


# ROTAS DE EXECUÇÃO
@app.route("/verificacao-login")
def verificacao_login():
    return 'Verificação de Login'


@app.route("/executar", methods=["POST"])
def executar():
    # Confere sintaxe do SKU
    sku = request.form['input-sku']
    if sku.count('-') != 2:
        return 'Referência inválida'
    else:
        referencia = sku[:sku.rfind('-')]

    # Confere cadastro do produto
    loja = request.form['input-loja']
    get_produto = magazord[loja].get_produto(codigo_produto=referencia, codigo_derivacao=sku)
    if get_produto['status'] == 'error':
        return 'Produto não encontrado'

    # Confere localidade antiga (existência)
    loc_antiga = request.form['input-loc-antiga']
    get_localidade_antiga = magazord[loja].get_localidade(1, loc_antiga)
    if not get_localidade_antiga and get_localidade_antiga != {}:
        return 'Localidade antiga não existe'

    # Confere localidade antiga (vinculação ao sku)
    get_produto_localidades = magazord[loja].get_produto_localidades(codigo_produto=sku)
    if loc_antiga not in get_produto_localidades:
        return 'Localidade antiga inválida para o produto'

    # Confere quantidade (disponível para ser movimentada)
    quantidade = request.form['input-quantidade']
    quantidade_disponivel = get_localidade_antiga[sku]['configurado'] - get_localidade_antiga[sku]['reservado']
    quantidade = quantidade_disponivel if not quantidade else int(quantidade)
    if quantidade > quantidade_disponivel:
        return f'Quantidade liberada pra ser movimentado: {quantidade_disponivel}'
    elif quantidade <= 0:
        return f'Quantidade de movimentação inválida: {quantidade}'

    # Confere localidade nova (existência)
    loc_nova = request.form['input-loc-nova']
    get_localidade_nova = magazord[loja].get_localidade(1, loc_nova)
    if not get_localidade_nova and get_localidade_nova != {}:
        return 'Localidade nova não existe (precisa ser criada)'

    observacao = request.form['input-observacao']

    # Movimentação válida

    # Vincula nova localidade caso não esteja ainda
    if loc_nova not in get_produto_localidades:
        vincula_loc = magazord[loja].post_vincular_localidade(
            produto_derivacao=sku, deposito=1, localidade=loc_nova
        )
        if vincula_loc['status'] == 'error':
            return f'Erro ao vincular localidade nova\n{vincula_loc}'
        else:
            get_localidade_nova = magazord[loja].get_localidade(1, loc_nova)

    # Insere quantidade na localidade nova
    insere_loc_nova = magazord[loja].put_produto_localidade(
        produto_derivacao=sku,
        deposito=1,
        localidade=loc_nova,
        quantidade_reservada=get_localidade_nova[sku]['reservado'],
        quantidade_configurada=get_localidade_nova[sku]['configurado'] + quantidade
    )
    if insere_loc_nova['status'] == 'error':
        return f'Erro ao inserir quantidade na localidade nova\n{insere_loc_nova}'

    # Remove quantidade da localidade antiga
    remove_loc_antiga = magazord[loja].put_produto_localidade(
        produto_derivacao=sku,
        deposito=1,
        localidade=loc_antiga,
        quantidade_reservada=get_localidade_antiga[sku]['reservado'],
        quantidade_configurada=get_localidade_antiga[sku]['configurado'] - quantidade
    )
    if remove_loc_antiga['status'] == 'error':
        return f'Erro ao remover quantidade da localidade antiga\n{remove_loc_antiga}'

    # Adiciona registro ao Firebase
    get_troca_localidade = firebase.get_item(caminho='', id_item='Troca-Localidade')
    id_item = 0 if not get_troca_localidade else len(get_troca_localidade)

    item = {
        'id': id_item,
        'loja': 'Rosa Azul' if loja == 'rosa-azul' else 'Use Force',
        'sku': sku,
        'loc-antiga': loc_antiga,
        'loc-nova': loc_nova,
        'quantidade': quantidade,
        'situacao': 'Alterado',
        'observacao': observacao,
        'usuario': 'Mikael Teste',
        'data-hora': datetime.now().strftime("%H:%M - %d/%m/%Y")
    }

    firebase.patch_item(caminho='Troca-Localidade', dados={id_item: item})

    return redirect('/troca-de-localidade')


@app.route("/cancelar/<id_item>", methods=["POST"])
def cancelar(id_item):
    return f'Cancelar o item de ID {id_item}'


# INICIALIZAÇÃO DA API
if __name__ == "__main__":
    app.run(debug=True)
