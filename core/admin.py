from django.contrib import admin
from .models import Colecao, Emprestimo, Favorito, Livro, MatchLiterario, Notificacao, Profile, Reserva


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("usuario", "telefone")
    search_fields = ("usuario__username", "telefone")


@admin.register(Livro)
class LivroAdmin(admin.ModelAdmin):
    list_display = ("titulo", "autor", "area", "estoque_total", "total_favoritos")
    list_filter = ("area",)
    search_fields = ("titulo", "autor")


@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "livro", "criado_em")
    search_fields = ("usuario__username", "livro__titulo")


@admin.register(MatchLiterario)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("livro", "usuario1", "usuario2", "criado_em")


@admin.register(Notificacao)
class NotifAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tipo", "mensagem", "lida", "criada_em")
    list_filter = ("tipo", "lida")


@admin.register(Colecao)
class ColecaoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "area", "destaque", "criada_em")
    filter_horizontal = ("livros",)


@admin.register(Emprestimo)
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = ("livro", "usuario", "status", "prazo_dias", "renovacoes",
                    "data_emprestimo", "data_prevista")
    list_filter = ("status",)


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("livro", "usuario", "atendida", "criada_em")
    list_filter = ("atendida",)
