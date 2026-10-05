def notificacoes_nao_lidas(request):
    if request.user.is_authenticated:
        return {"notificacoes_nao_lidas": request.user.notificacoes.filter(lida=False).count()}
    return {"notificacoes_nao_lidas": 0}
