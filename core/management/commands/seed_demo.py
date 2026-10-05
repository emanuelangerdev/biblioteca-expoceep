from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Colecao, Emprestimo, Favorito, Livro, Notificacao
from core.views import _criar_match_e_notificar


class Command(BaseCommand):
    help = "Popula o banco com dados de demonstração para a feira."

    def handle(self, *args, **kwargs):
        livros_data = [
            ("Dom Casmurro", "Machado de Assis", "Ficção", "Clássico da literatura brasileira sobre ciúme e dúvida.", 1899, 4),
            ("O Pequeno Príncipe", "Antoine de Saint-Exupéry", "Infantil", "Uma fábula poética sobre amizade e essencial invisível.", 1943, 5),
            ("Harry Potter e a Pedra Filosofal", "J.K. Rowling", "Fantasia", "O início da saga do bruxinho mais famoso do mundo.", 1997, 4),
            ("1984", "George Orwell", "Ficção Científica", "Distopia sobre vigilância e poder totalitário.", 1949, 3),
            ("O Hobbit", "J.R.R. Tolkien", "Fantasia", "A jornada de Bilbo até a Montanha Solitária.", 1937, 3),
            ("Orgulho e Preconceito", "Jane Austen", "Romance", "Elizabeth Bennet e Mr. Darcy num clássico romance.", 1813, 2),
            ("Código Limpo", "Robert C. Martin", "Tecnologia", "Manual essencial de boas práticas de programação.", 2008, 3),
            ("Sapiens", "Yuval Noah Harari", "Ciência", "Uma breve história da humanidade.", 2011, 3),
            ("A Culpa é das Estrelas", "John Green", "Romance", "História emocionante de Hazel e Gus.", 2012, 2),
            ("It: A Coisa", "Stephen King", "Suspense", "Terror no Derry com o palhaço Pennywise.", 1986, 2),
            ("Meditações", "Marco Aurélio", "Filosofia", "Reflexões estoicas de um imperador romano.", 180, 2),
            ("O Poder do Hábito", "Charles Duhigg", "Autoajuda", "Como os hábitos moldam nossa vida.", 2012, 3),
        ]
        for titulo, autor, area, desc, ano, est in livros_data:
            Livro.objects.get_or_create(
                titulo=titulo, defaults={"autor": autor, "area": area,
                                         "descricao": desc, "ano": ano, "estoque_total": est})

        # usuários demo (senha 123 — de propósito simples p/ feira)
        fones = {"ana": "11987654321", "bruno": "11912345678", "carla": "11955556666"}
        for uname in ["ana", "bruno", "carla"]:
            u, created = User.objects.get_or_create(username=uname,
                                                    defaults={"email": f"{uname}@demo.com"})
            if created:
                u.set_password("123")
                u.save()
            from core.models import Profile
            Profile.objects.update_or_create(
                usuario=u, defaults={"telefone": fones[uname]})

        ana = User.objects.get(username="ana")
        bruno = User.objects.get(username="bruno")
        livros = list(Livro.objects.all())
        # favoritos que geram matches de exemplo
        for livro in livros[:4]:
            for u in (ana, bruno):
                fav, created = Favorito.objects.get_or_create(usuario=u, livro=livro)
                if created:
                    _criar_match_e_notificar(fav)

        # coleções da equipe
        cols = [
            ("Primeiros passos na programação", "Tecnologia", "Base para quem deseja iniciar na área de tecnologia.", ["Código Limpo", "Sapiens"]),
            ("Romances essenciais", "Romance", "Clássicos e contemporâneos do romance.", ["Orgulho e Preconceito", "A Culpa é das Estrelas"]),
            ("Mundos de fantasia", "Fantasia", "Aventuras em universos imaginários.", ["O Hobbit", "Harry Potter e a Pedra Filosofal"]),
        ]
        for titulo, area, desc, titulos in cols:
            c, _ = Colecao.objects.get_or_create(titulo=titulo,
                                                 defaults={"area": area, "descricao": desc,
                                                           "destaque": True})
            for t in titulos:
                try:
                    c.livros.add(Livro.objects.get(titulo=t))
                except Livro.DoesNotExist:
                    pass

        # empréstimo exemplo
        if livros and not Emprestimo.objects.filter(usuario=ana).exists():
            Emprestimo.objects.create(
                usuario=ana, livro=livros[0],
                data_prevista=timezone.now() + timezone.timedelta(days=14))

        self.stdout.write(self.style.SUCCESS(
            "Dados de demonstração carregados. Usuários: ana/123, bruno/123, carla/123"))
