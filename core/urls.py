from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("livros/", views.livros_list, name="livros"),
    path("livros/novo/", views.livro_novo, name="livro_novo"),
    path("livros/<int:pk>/", views.livro_detalhe, name="livro_detalhe"),
    path("livros/<int:pk>/favoritar/", views.favoritar_toggle, name="favoritar"),
    path("livros/<int:pk>/emprestar/", views.emprestar, name="emprestar"),
    path("favoritos/", views.meus_favoritos, name="meus_favoritos"),
    path("ranking/", views.ranking, name="ranking"),
    path("matches/", views.meus_matches, name="matches"),
    path("notificacoes/", views.notificacoes, name="notificacoes"),
    path("notificacoes/<int:pk>/ler/", views.notificacao_ler, name="notificacao_ler"),
    path("notificacoes/ler-todas/", views.notificacoes_ler_todas, name="notificacoes_ler_todas"),
    path("colecoes/", views.colecoes_list, name="colecoes"),
    path("colecoes/nova/", views.colecao_nova, name="colecao_nova"),
    path("colecoes/<int:pk>/", views.colecao_detalhe, name="colecao_detalhe"),
    path("emprestimos/", views.meus_emprestimos, name="meus_emprestimos"),
    path("emprestimos/<int:pk>/devolver/", views.devolver, name="devolver"),
    path("emprestimos/<int:pk>/renovar/", views.renovar, name="renovar"),
    path("livros/<int:pk>/reservar/", views.reservar, name="reservar"),
    path("reservas/<int:pk>/cancelar/", views.cancelar_reserva, name="cancelar_reserva"),
    path("cadastro/", views.cadastro, name="cadastro"),
    path("perfil/", views.perfil, name="perfil"),
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
