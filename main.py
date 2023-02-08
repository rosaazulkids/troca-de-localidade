from flask import Flask, render_template, redirect, request, url_for
from padrao import Padrao
from api.magazord import Magazord
from api.firebase import Firebase
from datetime import datetime


app = Flask(__name__)
padrao = Padrao()


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
magazord = {'Rosa Azul': mz_rosa_azul, 'Use Force': mz_use_force}


# INICIALIZAÇÃO API's - FIREBASE
firebase = Firebase()


@app.route("/")
def homepage():
    return redirect(url_for('troca_de_localidade'))


@app.route("/troca-de-localidade/<id_item>")
def troca_de_localidade_id_item(id_item: int):
    global padrao
    lista = list(filter(None, firebase.get_item(caminho='', id_item='Troca-Localidade')))
    for item in lista:
        if str(item['id']) == str(id_item):
            return render_template("troca_de_localidade.html", lista_troca_localidade=reversed(lista),
                                   id_item=str(id_item), item=item,
                                   usuario_padrao=padrao.usuario, loja_padrao=padrao.loja)

    return f'Item de ID {id_item} não encontrado'


@app.route("/troca-de-localidade")
def troca_de_localidade():
    lista = list(filter(None, firebase.get_item(caminho='', id_item='Troca-Localidade')))
    item_none = {'sku': '', 'loc-antiga': '', 'loc-nova': '', 'quantidade': '', 'observacao': ''}
    global padrao
    return render_template("troca_de_localidade.html", lista_troca_localidade=reversed(lista),
                           id_item='', item=item_none,
                           usuario_padrao=padrao.usuario, loja_padrao=padrao.loja)


@app.route("/executar", methods=["POST"])
def executar():
    usuario = request.form['input-user']
    loja = request.form['input-loja']
    sku = request.form['input-sku']
    loc_antiga = request.form['input-loc-antiga']
    loc_nova = request.form['input-loc-nova']
    quantidade = request.form['input-quantidade']
    observacao = request.form['input-observacao']

    situacao = 'Pendente'

    # Confere campos obrigatórios
    if not usuario:
        return 'Preencha o campo Usuário'
    elif not sku:
        return 'Preencha o campo Referência (SKU)'
    elif not loc_antiga:
        return 'Preencha o campo Localidade Antiga'
    elif not loc_nova:
        return 'Preencha o campo Localidade Nova'

    # Confere sintaxe do SKU
    if sku.count('-') != 2:
        observacao = 'Referência inválida'
    else:
        referencia = sku[:sku.rfind('-')]

        # Confere cadastro do produto
        loja = request.form['input-loja']
        get_produto = magazord[loja].get_produto(codigo_produto=referencia, codigo_derivacao=sku)
        if get_produto['status'] == 'error':
            observacao = 'Produto não encontrado'

        else:
            # Confere localidade antiga (existência)
            loc_antiga = request.form['input-loc-antiga']
            get_localidade_antiga = magazord[loja].get_localidade(1, loc_antiga)
            if not get_localidade_antiga and get_localidade_antiga != {}:
                observacao = 'Localidade antiga não existe'

            else:
                # Confere localidade antiga (vinculação ao sku)
                get_produto_localidades = magazord[loja].get_produto_localidades(codigo_produto=sku)
                if loc_antiga not in get_produto_localidades:
                    observacao = 'Localidade antiga inválida para o produto'

                else:
                    # Confere quantidade (disponível para ser movimentada)
                    quantidade = request.form['input-quantidade']
                    quantidade_disponivel = \
                        get_localidade_antiga[sku]['configurado'] - get_localidade_antiga[sku]['reservado']
                    quantidade = quantidade_disponivel if not quantidade else int(quantidade)
                    if quantidade > quantidade_disponivel:
                        observacao = f'Quantidade liberada pra ser movimentado: {quantidade_disponivel}'
                    elif quantidade <= 0:
                        observacao = f'Quantidade de movimentação inválida: {quantidade}'
                    else:
                        # Confere localidade nova (existência)
                        loc_nova = request.form['input-loc-nova']
                        get_localidade_nova = magazord[loja].get_localidade(1, loc_nova)
                        if not get_localidade_nova and get_localidade_nova != {}:
                            observacao = 'Localidade nova não existe (precisa ser criada)'

                        else:
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
                                situacao = f'Erro ao inserir quantidade na localidade nova'

                            else:
                                # Remove quantidade da localidade antiga
                                remove_loc_antiga = magazord[loja].put_produto_localidade(
                                    produto_derivacao=sku,
                                    deposito=1,
                                    localidade=loc_antiga,
                                    quantidade_reservada=get_localidade_antiga[sku]['reservado'],
                                    quantidade_configurada=get_localidade_antiga[sku]['configurado'] - quantidade
                                )
                                if remove_loc_antiga['status'] == 'error':
                                    situacao = 'Erro ao remover quantidade da localidade antiga'
                                else:
                                    situacao = 'Alterado'

    # Adiciona registro ao Firebase
    if not request.form['display-id']:
        get_troca_localidade = firebase.get_item(caminho='', id_item='Troca-Localidade')
        id_item = 0 if not get_troca_localidade else int(get_troca_localidade[-1]['id']) + 1
    else:
        id_item = int(request.form['display-id'])

    item = {
        'id': int(id_item),
        'loja': loja,
        'sku': sku,
        'loc-antiga': loc_antiga,
        'loc-nova': loc_nova,
        'quantidade': quantidade,
        'situacao': situacao,
        'observacao': observacao,
        'usuario': usuario,
        'data-hora': datetime.now().strftime("%H:%M - %d/%m/%Y")
    }

    firebase.patch_item(caminho='Troca-Localidade', dados={id_item: item})

    # Adiciona usuário, loja e observação padrões
    global padrao
    if not padrao.usuario or not padrao.loja:
        padrao = Padrao(usuario=usuario, loja=loja)

    return redirect(url_for('troca_de_localidade'))


@app.route("/cancelar/<id_item>", methods=["POST"])
def cancelar(id_item):
    item = firebase.get_item(caminho='Troca-Localidade', id_item=id_item)

    time_mov, date_mov = item['data-hora'].split(' - ')
    day_mov = date_mov.split('/')[0]
    hora_mov, min_mov = time_mov.split(':')
    minutos_mov = (int(hora_mov) * 60) + int(min_mov)

    hora_now, min_now, day_now = datetime.now().strftime("%H:%M:%d").split(':')
    minutos_now = (int(hora_now) * 60) + int(min_now)

    if day_now != day_mov or minutos_now - minutos_mov > 15:
        return 'Já se passaram 15 minutos da movimentação. É impossível cancelar'

    return redirect(url_for('troca_de_localidade'))


@app.route("/excluir/<id_item>", methods=["POST"])
def excluir(id_item):
    firebase.delete_item(caminho='Troca-Localidade', id_item=id_item)
    return redirect(url_for('troca_de_localidade'))


# INICIALIZAÇÃO DA API
if __name__ == "__main__":
    # app.run(debug=True)
    app.run()
