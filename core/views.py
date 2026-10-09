from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CadastroForm, ColecaoForm, LivroForm, TelefoneForm
from .models import (AREAS, Colecao, Emprestimo, Favorito, Livro,
                     MatchLiterario, Notificacao, Profile, Reserva)


def _criar_match_e_notificar(novo_favorito):
    """Ao favoritar, cria matches com quem já favoritou o mesmo livro."""
    livro = novo_favorito.livro
    eu = novo_favorito.usuario
    outros_ids = (
        Favorito.objects.filter(livro=livro).exclude(usuario=eu)
        .values_list("usuario_id", flat=True).distinct()
    )
    criados = 0
    for outro_id in outros_ids:
        outro = User.objects.get(id=outro_id)
        u1, u2 = (eu, outro) if eu.id < outro.id else (outro, eu)
        match, created = MatchLiterario.objects.get_or_create(
            livro=livro, usuario1=u1, usuario2=u2)
        if created:
            criados += 1
            Notificacao.objects.create(
                usuario=outro, tipo="match",
                mensagem=f"Novo match literário: {eu.username} também favoritou “{livro.titulo}”.",
                link="/matches/")
            Notificacao.objects.create(
                usuario=eu, tipo="match",
                mensagem=f"Novo match literário: você e {outro.username} favoritaram “{livro.titulo}”.",
                link="/matches/")
    return criados


def home(request):
    ranking = (Livro.objects.annotate(n_fav=Count("favoritos"))
               .order_by("-n_fav", "titulo")[:5])
    colecoes = Colecao.objects.prefetch_related("livros")[:3]
    total_livros = Livro.objects.count()
    total_matches = MatchLiterario.objects.count()
    total_emprestimos = Emprestimo.objects.filter(status__in=["ativo", "atrasado"]).count()
    recentes = Livro.objects.order_by("-criado_em")[:6]
    return render(request, "core/home.html", {
        "ranking": ranking, "colecoes": colecoes, "recentes": recentes,
        "total_livros": total_livros, "total_matches": total_matches,
        "total_emprestimos": total_emprestimos,
    })


def livros_list(request):
    q = request.GET.get("q", "").strip()
    area = request.GET.get("area", "")
    livros = Livro.objects.annotate(n_fav=Count("favoritos")).order_by("-n_fav", "titulo")
    if q:
        livros = livros.filter(
            Q(titulo__icontains=q) | Q(autor__icontains=q) | Q(descricao__icontains=q))
    if area:
        livros = livros.filter(area=area)
    fav_ids = set()
    if request.user.is_authenticated:
        fav_ids = set(request.user.favoritos.values_list("livro_id", flat=True))
    return render(request, "core/livros_list.html", {
        "livros": livros, "q": q, "area": area, "areas": AREAS, "fav_ids": fav_ids,
    })


def livro_detalhe(request, pk):
    livro = get_object_or_404(Livro.objects.annotate(n_fav=Count("favoritos")), pk=pk)
    ja_favoritou = request.user.is_authenticated and Favorito.objects.filter(
        usuario=request.user, livro=livro).exists()
    quem_favoritou = Favorito.objects.filter(livro=livro).select_related("usuario")
    if request.user.is_authenticated:
        quem_favoritou = quem_favoritou.exclude(usuario=request.user)
    quem_favoritou = quem_favoritou[:8]
    meu_emprestimo = None
    minha_reserva = None
    fila_reserva = Reserva.objects.filter(livro=livro, atendida=False).count()
    if request.user.is_authenticated:
        meu_emprestimo = (Emprestimo.objects
                          .filter(usuario=request.user, livro=livro,
                                  status__in=["ativo", "atrasado"]).first())
        minha_reserva = (Reserva.objects
                         .filter(usuario=request.user, livro=livro, atendida=False).first())
    return render(request, "core/livro_detalhe.html", {
        "livro": livro, "ja_favoritou": ja_favoritou,
        "quem_favoritou": quem_favoritou, "meu_emprestimo": meu_emprestimo,
        "minha_reserva": minha_reserva, "fila_reserva": fila_reserva,
        "prazos": Emprestimo.PRAZOS, "prazo_padrao": Emprestimo.PRAZO_PADRAO,
        "max_renovacoes": Emprestimo.MAX_RENOVACOES,
    })


@login_required
def favoritar_toggle(request, pk):
    livro = get_object_or_404(Livro, pk=pk)
    fav, created = Favorito.objects.get_or_create(usuario=request.user, livro=livro)
    if not created:
        # desfavoritar: remove matches? Não — mantém histórico, só remove fav (modo feira, flexível)
        fav.delete()
        messages.info(request, f"“{livro.titulo}” removido dos favoritos.")
    else:
        n = _criar_match_e_notificar(fav)
        if n:
            messages.success(
                request,
                f"Match literário registrado: {n} pessoa(s) também favoritaram "
                f"“{livro.titulo}”. Consulte a página de matches.")
        else:
            messages.success(request, f"“{livro.titulo}” adicionado aos favoritos.")
    return redirect(request.META.get("HTTP_REFERER", "livros"))


@login_required
def meus_favoritos(request):
    favs = Favorito.objects.filter(usuario=request.user).select_related("livro")
    return render(request, "core/meus_favoritos.html", {"favs": favs})


def ranking(request):
    livros = (Livro.objects.annotate(n_fav=Count("favoritos"))
              .order_by("-n_fav", "titulo"))
    max_fav = livros[0].n_fav if livros else 0
    return render(request, "core/ranking.html", {"livros": livros, "max_fav": max_fav or 1})


@login_required
def meus_matches(request):
    matches = (MatchLiterario.objects
               .filter(Q(usuario1=request.user) | Q(usuario2=request.user))
               .select_related("livro", "usuario1", "usuario2"))
    cards = []
    for m in matches:
        outro = m.usuario2 if m.usuario1 == request.user else m.usuario1
        profile, _ = Profile.objects.get_or_create(usuario=outro)
        publico = profile.telefone_publico
        cards.append({
            "match": m, "outro": outro,
            "telefone": profile.telefone_somente_digitos if publico else "",
            "wa_url": profile.whatsapp_url(m.livro.titulo),
            "telefone_publico": publico,
        })
    return render(request, "core/matches.html", {"cards": cards})


@login_required
def notificacoes(request):
    notifs = Notificacao.objects.filter(usuario=request.user)
    return render(request, "core/notificacoes.html", {"notifs": notifs})


@login_required
def notificacao_ler(request, pk):
    n = get_object_or_404(Notificacao, pk=pk, usuario=request.user)
    n.lida = True
    n.save()
    return redirect(n.link or "notificacoes")


@login_required
def notificacoes_ler_todas(request):
    request.user.notificacoes.filter(lida=False).update(lida=True)
    messages.success(request, "Todas as notificações foram marcadas como lidas.")
    return redirect("notificacoes")


def colecoes_list(request):
    area = request.GET.get("area", "")
    colecoes = Colecao.objects.prefetch_related("livros").all()
    if area:
        colecoes = colecoes.filter(area=area)
    return render(request, "core/colecoes.html", {
        "colecoes": colecoes, "areas": AREAS, "area": area})


def colecao_detalhe(request, pk):
    c = get_object_or_404(Colecao.objects.prefetch_related("livros"), pk=pk)
    fav_ids = set()
    if request.user.is_authenticated:
        fav_ids = set(request.user.favoritos.values_list("livro_id", flat=True))
    return render(request, "core/colecao_detalhe.html",
                  {"c": c, "fav_ids": fav_ids})


@login_required
def emprestar(request, pk):
    """Registra um empréstimo com o prazo escolhido pelo usuário."""
    livro = get_object_or_404(Livro, pk=pk)
    try:
        prazo = int(request.POST.get("prazo", Emprestimo.PRAZO_PADRAO))
    except (TypeError, ValueError):
        prazo = Emprestimo.PRAZO_PADRAO
    if prazo not in [p for p, _ in Emprestimo.PRAZOS]:
        prazo = Emprestimo.PRAZO_PADRAO
    if livro.disponiveis <= 0:
        messages.error(
            request,
            "Não há exemplares disponíveis no momento. "
            "Você pode entrar na fila de reserva.")
        return redirect("livro_detalhe", pk=pk)
    ja = Emprestimo.objects.filter(usuario=request.user, livro=livro,
                                    status__in=["ativo", "atrasado"]).exists()
    if ja:
        messages.info(request, "Você já possui um empréstimo em aberto para esta obra.")
        return redirect("livro_detalhe", pk=pk)
    emp = Emprestimo.objects.create(
        usuario=request.user, livro=livro, prazo_dias=prazo,
        data_prevista=timezone.now() + timezone.timedelta(days=prazo))
    Notificacao.objects.create(
        usuario=request.user, tipo="emprestimo",
        mensagem=f"Empréstimo registrado: “{livro.titulo}”, com devolução até "
                 f"{emp.data_prevista:%d/%m/%Y}.",
        link="/emprestimos/")
    messages.success(
        request,
        f"Empréstimo registrado. Retire “{livro.titulo}” no balcão e devolva até "
        f"{emp.data_prevista:%d/%m/%Y}.")
    return redirect("meus_emprestimos")


@login_required
def renovar(request, pk):
    emp = get_object_or_404(Emprestimo, pk=pk, usuario=request.user)
    if emp.renovar():
        messages.success(
            request,
            f"Empréstimo renovado. Novo prazo de devolução: {emp.data_prevista:%d/%m/%Y} "
            f"({emp.renovacoes}/{Emprestimo.MAX_RENOVACOES} renovações utilizadas).")
    else:
        messages.error(
            request,
            "Não foi possível renovar. Verifique se o empréstimo está ativo, "
            "se ainda há renovações disponíveis e se não existe fila de reserva.")
    return redirect("meus_emprestimos")


@login_required
def devolver(request, pk):
    emp = get_object_or_404(Emprestimo, pk=pk, usuario=request.user)
    if emp.status in ("ativo", "atrasado"):
        emp.status = "devolvido"
        emp.data_devolucao = timezone.now()
        emp.save()
        if emp.dias_atraso:
            messages.warning(
                request,
                f"Devolução registrada com {emp.dias_atraso} dia(s) de atraso. "
                f"Multa simulada: R$ {emp.multa_simulada:.2f}.")
        else:
            messages.success(request, f"Devolução de “{emp.livro.titulo}” registrada. Obrigado.")
        _atender_fila_reserva(emp.livro)
    return redirect("meus_emprestimos")


def _atender_fila_reserva(livro):
    """Avisa o primeiro da fila quando um exemplar é devolvido."""
    proxima = Reserva.objects.filter(livro=livro, atendida=False).first()
    if proxima and livro.disponiveis > 0:
        proxima.atendida = True
        proxima.atendida_em = timezone.now()
        proxima.save()
        Notificacao.objects.create(
            usuario=proxima.usuario, tipo="reserva",
            mensagem=f"Exemplar de “{livro.titulo}” disponível para retirada. "
                     "Prazo de retirada: 2 dias úteis.",
            link="/emprestimos/")


@login_required
def reservar(request, pk):
    livro = get_object_or_404(Livro, pk=pk)
    if livro.disponiveis > 0:
        messages.info(request, "Há exemplares disponíveis. Solicite o empréstimo diretamente.")
        return redirect("livro_detalhe", pk=pk)
    ja = Reserva.objects.filter(usuario=request.user, livro=livro, atendida=False).exists()
    if ja:
        messages.info(request, "Você já está na fila de reserva desta obra.")
        return redirect("livro_detalhe", pk=pk)
    reserva = Reserva.objects.create(usuario=request.user, livro=livro)
    messages.success(
        request,
        f"Reserva registrada. Você é o número {reserva.posicao} na fila de “{livro.titulo}”.")
    return redirect("meus_emprestimos")


@login_required
def cancelar_reserva(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk, usuario=request.user, atendida=False)
    reserva.delete()
    messages.success(request, "Reserva cancelada.")
    return redirect("meus_emprestimos")


@login_required
def meus_emprestimos(request):
    emps = Emprestimo.objects.filter(usuario=request.user).select_related("livro")
    for e in emps:
        if e.status == "ativo" and timezone.now() > e.data_prevista:
            e.status = "atrasado"
            e.save()
    ativos = [e for e in emps if e.status in ("ativo", "atrasado")]
    historico = [e for e in emps if e.status == "devolvido"][:10]
    reservas = list(Reserva.objects.filter(usuario=request.user, atendida=False)
                    .select_related("livro"))
    multa_total = round(sum(e.multa_simulada for e in ativos if e.status == "atrasado"), 2)
    return render(request, "core/emprestimos.html", {
        "ativos": ativos, "historico": historico, "reservas": reservas,
        "multa_total": multa_total,
        "max_renovacoes": Emprestimo.MAX_RENOVACOES,
    })


@login_required
def livro_novo(request):
    if request.method == "POST":
        form = LivroForm(request.POST, request.FILES)
        if form.is_valid():
            livro = form.save()
            messages.success(request, f"Obra “{livro.titulo}” cadastrada no acervo.")
            return redirect("livro_detalhe", pk=livro.pk)
    else:
        form = LivroForm()
    return render(request, "core/form.html",
                  {"form": form, "titulo": "Cadastrar livro", "sub": "Adicione uma obra ao acervo da feira"})


@login_required
def colecao_nova(request):
    if request.method == "POST":
        form = ColecaoForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.criada_por = request.user
            c.save()
            form.save_m2m()
            messages.success(request, f"Lista de recomendação “{c.titulo}” criada.")
            return redirect("colecao_detalhe", pk=c.pk)
    else:
        form = ColecaoForm()
    return render(request, "core/form.html",
                  {"form": form, "titulo": "Nova lista de recomendação",
                   "sub": "Organize por área, interesse ou afinidade"})


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            Notificacao.objects.create(
                usuario=user, tipo="sistema",
                mensagem="Bem-vindo à BiblioMatch. Favorite obras para encontrar seu match literário.",
                link="/livros/")
            messages.success(request, f"Bem-vindo, {user.username}. Explore o acervo.")
            return redirect("home")
    else:
        form = CadastroForm()
    return render(request, "core/cadastro.html", {"form": form})


def perfil(request):
    if not request.user.is_authenticated:
        return redirect("login")
    u = request.user
    profile, _ = Profile.objects.get_or_create(usuario=u)
    if request.method == "POST":
        form = TelefoneForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Número de telefone atualizado.")
            return redirect("perfil")
    else:
        form = TelefoneForm(instance=profile)
    return render(request, "core/perfil.html", {
        "n_fav": u.favoritos.count(),
        "n_matches": MatchLiterario.objects.filter(
            Q(usuario1=u) | Q(usuario2=u)).count(),
        "n_emps": u.emprestimos.filter(status__in=["ativo", "atrasado"]).count(),
        "emps": u.emprestimos.select_related("livro")[:5],
        "favs": u.favoritos.select_related("livro")[:6],
        "form": form,
    })
