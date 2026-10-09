import re
from urllib.parse import quote

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

AREAS = [
    ("Ficção", "Ficção"),
    ("Fantasia", "Fantasia"),
    ("Romance", "Romance"),
    ("Suspense", "Suspense / Mistério"),
    ("Ficção Científica", "Ficção Científica"),
    ("Tecnologia", "Tecnologia"),
    ("Ciência", "Ciência"),
    ("História", "História"),
    ("Filosofia", "Filosofia"),
    ("Autoajuda", "Autoajuda"),
    ("Negócios", "Negócios"),
    ("Educação", "Educação"),
    ("Arte", "Arte"),
    ("Poesia", "Poesia"),
    ("Infantil", "Infantil"),
]


class Profile(models.Model):
    """Telefone de contato do usuário (usado no botão WhatsApp do match)."""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    telefone = models.CharField(max_length=20, blank=False,
                                help_text="Somente números com DDD. Ex: 11999998888")
    telefone_publico = models.BooleanField(
        default=True,
        help_text="Se marcado, outros leitores com match poderão ver seu número.")

    def __str__(self):
        return f"{self.usuario.username}: {self.telefone or '—'}"

    @property
    def telefone_somente_digitos(self):
        return re.sub(r"\D", "", self.telefone or "")

    def whatsapp_url(self, livro_titulo=""):
        if not self.telefone_publico:
            return ""
        fone = self.telefone_somente_digitos
        if not fone:
            return ""
        msg = (f"Olá! Tivemos um match literário no BiblioMatch "
               f"— ambos favoritaram “{livro_titulo}”. Vamos conversar sobre a obra?")
        return f"https://wa.me/{fone}?text={quote(msg)}"


@receiver(post_save, sender=User)
def _criar_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(usuario=instance)


class Livro(models.Model):
    titulo = models.CharField(max_length=200)
    autor = models.CharField(max_length=150)
    area = models.CharField(max_length=50, choices=AREAS, default="Ficção")
    descricao = models.TextField(blank=True)
    ano = models.PositiveIntegerField(null=True, blank=True)
    isbn = models.CharField(max_length=30, blank=True)
    capa_url = models.URLField(blank=True, help_text="Link da capa (opcional, ideal p/ feira)")
    capa = models.ImageField(upload_to="capas/", blank=True, null=True)
    estoque_total = models.PositiveIntegerField(default=3)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["titulo"]

    def __str__(self):
        return f"{self.titulo} — {self.autor}"

    @property
    def total_favoritos(self):
        return self.favoritos.count()

    @property
    def emprestimos_ativos(self):
        return self.emprestimos.filter(status="ativo").count()

    @property
    def disponiveis(self):
        return max(0, self.estoque_total - self.emprestimos_ativos)

    def capa_src(self):
        if self.capa:
            return self.capa.url
        if self.capa_url:
            return self.capa_url
        # placeholder com inicial — sem dependência externa
        return ""


class Favorito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favoritos")
    livro = models.ForeignKey(Livro, on_delete=models.CASCADE, related_name="favoritos")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("usuario", "livro")
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Favorito: {self.usuario.username} — {self.livro.titulo}"


class MatchLiterario(models.Model):
    livro = models.ForeignKey(Livro, on_delete=models.CASCADE, related_name="matches")
    usuario1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="matches_como_1")
    usuario2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="matches_como_2")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(fields=["livro", "usuario1", "usuario2"], name="match_unico")
        ]

    def __str__(self):
        return f"Match {self.usuario1.username} + {self.usuario2.username} ({self.livro.titulo})"

    def outro(self, user):
        return self.usuario2 if user == self.usuario1 else self.usuario1


class Notificacao(models.Model):
    TIPOS = [
        ("match", "Match literário"),
        ("emprestimo", "Empréstimo"),
        ("reserva", "Reserva"),
        ("sistema", "Sistema"),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notificacoes")
    tipo = models.CharField(max_length=20, choices=TIPOS, default="sistema")
    mensagem = models.CharField(max_length=280)
    link = models.CharField(max_length=200, blank=True, default="")
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]

    def __str__(self):
        return f"[{self.tipo}] {self.usuario.username}: {self.mensagem[:40]}"


class Colecao(models.Model):
    """Listas de recomendações elaboradas pela equipe."""
    titulo = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    area = models.CharField(max_length=50, choices=AREAS, default="Ficção")
    livros = models.ManyToManyField(Livro, related_name="colecoes", blank=True)
    criada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    destaque = models.BooleanField(default=False)

    class Meta:
        ordering = ["-destaque", "-criada_em"]

    def __str__(self):
        return self.titulo


class Emprestimo(models.Model):
    STATUS = [
        ("ativo", "Ativo"),
        ("devolvido", "Devolvido"),
        ("atrasado", "Atrasado"),
    ]
    PRAZOS = [(7, "7 dias"), (14, "14 dias"), (21, "21 dias")]
    PRAZO_PADRAO = 14
    MAX_RENOVACOES = 2
    MULTA_POR_DIA = 2.0  # valor simulado em R$ por dia de atraso

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="emprestimos")
    livro = models.ForeignKey(Livro, on_delete=models.CASCADE, related_name="emprestimos")
    data_emprestimo = models.DateTimeField(default=timezone.now)
    data_prevista = models.DateTimeField(null=True, blank=True)
    data_devolucao = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="ativo")
    prazo_dias = models.PositiveIntegerField(default=PRAZO_PADRAO)
    renovacoes = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-data_emprestimo"]

    def __str__(self):
        return f"{self.livro.titulo} — {self.usuario.username} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.data_prevista:
            self.data_prevista = timezone.now() + timezone.timedelta(days=self.prazo_dias)
        if self.status == "ativo" and timezone.now() > self.data_prevista:
            self.status = "atrasado"
        super().save(*args, **kwargs)

    @property
    def dias_restantes(self):
        return (self.data_prevista - timezone.now()).days

    @property
    def dias_atraso(self):
        ref = self.data_devolucao or timezone.now()
        return max(0, (ref - self.data_prevista).days)

    @property
    def multa_simulada(self):
        return round(self.dias_atraso * self.MULTA_POR_DIA, 2)

    @property
    def progresso(self):
        """Fração do prazo já decorrida (0–1), para a barra de progresso."""
        total = (self.data_prevista - self.data_emprestimo).total_seconds()
        if total <= 0:
            return 1.0
        decorrido = (min(timezone.now(), self.data_prevista) - self.data_emprestimo).total_seconds()
        ref = decorrido if self.status != "devolvido" else total
        return max(0.0, min(1.0, ref / total))

    def pode_renovar(self):
        if self.status != "ativo" or self.renovacoes >= self.MAX_RENOVACOES:
            return False
        return not Reserva.objects.filter(livro=self.livro, atendida=False).exists()

    def renovar(self):
        if not self.pode_renovar():
            return False
        self.data_prevista = self.data_prevista + timezone.timedelta(days=self.prazo_dias)
        self.renovacoes += 1
        self.save()
        return True


class Reserva(models.Model):
    """Fila de espera por exemplar indisponível (ordem de chegada)."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reservas")
    livro = models.ForeignKey(Livro, on_delete=models.CASCADE, related_name="reservas")
    criada_em = models.DateTimeField(auto_now_add=True)
    atendida = models.BooleanField(default=False)
    atendida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["criada_em"]

    def __str__(self):
        return f"Reserva: {self.livro.titulo} — {self.usuario.username}"

    @property
    def posicao(self):
        fila = Reserva.objects.filter(livro=self.livro, atendida=False).order_by("criada_em")
        for i, r in enumerate(fila, start=1):
            if r.pk == self.pk:
                return i
        return 0
