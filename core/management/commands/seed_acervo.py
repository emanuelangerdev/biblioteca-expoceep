from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from core.models import Colecao, Livro

# Open Library Covers API. Tamanho M: mais leve e estável que o L
# (o L às vezes redireciona p/ o cluster do archive.org e sofre
# rate-limit de 100 req/5min por IP — ruim no dia da feira).
COV = "https://covers.openlibrary.org/b/id/{}-M.jpg"

# (titulo, autor, area, descricao, ano, estoque, cover_id)
# Capas: Open Library Covers API — os 30 IDs foram conferidos um a um na
# Search API (openlibrary.org/search.json) em out/2026, preferindo edições
# em português quando disponíveis. Se algum dia uma capa sumir, rode
# `seed_acervo --baixar-capas` (guarda cópia local p/ funcionar offline).
LIVROS = [
    # ── 10 CLÁSSICOS ──
    ("Dom Quixote", "Miguel de Cervantes", "Ficção",
     "O cavaleiro da triste figura e seu fiel Sancho Pança em aventuras que fundaram o romance moderno.", 1605, 3, 4918434),
    ("Orgulho e Preconceito", "Jane Austen", "Romance",
     "Elizabeth Bennet e Mr. Darcy entre orgulho, preconceito e declarações inesquecíveis.", 1813, 3, 14348537),
    ("Frankenstein", "Mary Shelley", "Ficção",
     "Victor Frankenstein dá vida à criatura e levanta o debate sobre ciência e responsabilidade.", 1818, 3, 12356249),
    ("Jane Eyre", "Charlotte Brontë", "Romance",
     "Órfã e decidida, Jane Eyre enfrenta Thornfield Hall e seus segredos.", 1847, 2, 8235363),
    ("Moby Dick", "Herman Melville", "Ficção",
     "A obsessão do capitão Ahab pela baleia branca em alto-mar.", 1851, 2, 10544254),
    ("Crime e Castigo", "Fiódor Dostoiévski", "Ficção",
     "Raskólnikov comete um crime e mergulha em culpa, confissão e redenção.", 1866, 3, 13116014),
    ("Dom Casmurro", "Machado de Assis", "Ficção",
     "Bentinho reconstrói a história com Capitu: traiu ou não traiu? O maior debate da literatura brasileira.", 1899, 4, 647501),
    ("A Metamorfose", "Franz Kafka", "Ficção",
     "Gregor Samsa acorda transformado em inseto e a família precisa lidar com o absurdo.", 1915, 2, 9646280),
    ("1984", "George Orwell", "Ficção Científica",
     "Winston Smith vive sob o Grande Irmão numa distopia sobre vigilância e poder.", 1949, 4, 9267242),
    ("O Pequeno Príncipe", "Antoine de Saint-Exupéry", "Infantil",
     "Um principezinho de outro planeta ensina que o essencial é invisível aos olhos.", 1943, 5, 15231561),
    # ── 10 CONTEMPORÂNEOS ──
    ("Torto Arado", "Itamar Vieira Junior", "Ficção",
     "As irmãs Bibiana e Belonísia no sertão baiano: trabalho, fé e resistência. Vencedor do Jabuti.", 2019, 3, 12369648),
    ("Tudo é Rio", "Carla Madeira", "Romance",
     "Lucy, Venâncio e Dalva num triângulo de desejo, violência e perdão às margens do rio.", None, 2, 14631316),
    ("A Biblioteca da Meia-Noite", "Matt Haig", "Fantasia",
     "Entre a vida e a morte, Nora Seed pode viver todas as vidas que deixou para trás.", 2020, 3, 10313767),
    ("É Assim que Acaba", "Colleen Hoover", "Romance",
     "Lily precisa decidir entre o amor e a coragem de quebrar um ciclo de violência.", 2016, 3, 10473609),
    ("Pessoas Normais", "Sally Rooney", "Romance",
     "Connell e Marianne se atraem e se afastam da escola à universidade, entre classe e afeto.", 2018, 2, 8794265),
    ("Klara e o Sol", "Kazuo Ishiguro", "Ficção Científica",
     "Uma amiga artificial observa o mundo e aprende o que significa amar alguém.", 2021, 2, 10648686),
    ("Daisy Jones & The Six", "Taylor Jenkins Reid", "Ficção",
     "A ascensão e a queda da banda mais amada dos anos 1970, em formato de entrevista.", 2019, 2, 8742674),
    ("A Paciente Silenciosa", "Alex Michaelides", "Suspense",
     "Alicia atirou no marido e nunca mais falou. O terapeuta Theo quer descobrir o porquê.", 2019, 3, 9407338),
    ("Os Sete Maridos de Evelyn Hugo", "Taylor Jenkins Reid", "Romance",
     "A estrela de Hollywood Evelyn Hugo conta sua vida — e seus sete casamentos — a uma jornalista.", 2017, 3, 8354226),
    ("Verity", "Colleen Hoover", "Suspense",
     "Uma escritora fantasma encontra o manuscrito secreto de Verity e descobre algo aterrorizante.", None, 2, 8747160),
    # ── 10 FAMOSOS ──
    ("Harry Potter e a Pedra Filosofal", "J.K. Rowling", "Fantasia",
     "Harry descobre que é bruxo e parte para Hogwarts no início da saga mais famosa do mundo.", 1997, 5, 15155833),
    ("O Hobbit", "J.R.R. Tolkien", "Fantasia",
     "Bilbo Bolseiro troca o conforto do Condado por dragões, anões e um anel misterioso.", 1937, 4, 14627509),
    ("Jogos Vorazes", "Suzanne Collins", "Ficção Científica",
     "Katniss se oferece no lugar da irmã para lutar até a morte na arena da Capital.", 2008, 4, 12646537),
    ("O Código Da Vinci", "Dan Brown", "Suspense",
     "Robert Langdon corre por Paris e Londres atrás de um segredo guardado por séculos.", 2003, 3, 9255229),
    ("Crepúsculo", "Stephenie Meyer", "Romance",
     "Bella Swan se apaixona por Edward Cullen, o vampiro mais famoso da cultura pop.", 2005, 3, 12641977),
    ("O Leão, a Feiticeira e o Guarda-Roupa", "C.S. Lewis", "Fantasia",
     "Quatro irmãos atravessam o guarda-roupa e chegam a Nárnia, terra de Aslam.", 1950, 3, 8441376),
    ("O Diário de Anne Frank", "Anne Frank", "História",
     "O diário real de uma menina judia escondida durante a Segunda Guerra Mundial.", 1947, 3, 13526331),
    ("O Alquimista", "Paulo Coelho", "Ficção",
     "O pastor Santiago segue sua lenda pessoal pelo deserto em busca do tesouro.", 1988, 4, 7414780),
    ("A Culpa é das Estrelas", "John Green", "Romance",
     "Hazel e Gus se conhecem num grupo de apoio e vivem um amor inesquecível.", 2012, 3, 7418786),
    ("It: A Coisa", "Stephen King", "Suspense",
     "O Clube dos Otários enfrenta Pennywise nos esgotos de Derry.", 1986, 2, 8569284),
]

COLECOES = [
    ("Clássicos essenciais", "Ficção",
     "Os gigantes que todo leitor deveria conhecer um dia.",
     ["Dom Quixote", "Orgulho e Preconceito", "Frankenstein", "Dom Casmurro", "1984", "O Pequeno Príncipe"],
     True),
    ("Contemporâneos para começar", "Ficção",
     "Sucessos recentes para entrar no ritmo da leitura.",
     ["Torto Arado", "A Biblioteca da Meia-Noite", "É Assim que Acaba", "Pessoas Normais", "Daisy Jones & The Six"],
     True),
    ("Famosos que todo mundo leu", "Fantasia",
     "Aqueles que viraram filme, série e conversa de corredor.",
     ["Harry Potter e a Pedra Filosofal", "O Hobbit", "Jogos Vorazes", "O Código Da Vinci", "O Alquimista"],
     True),
]


class Command(BaseCommand):
    help = "Inicializa o acervo com 30 livros (10 clássicos, 10 contemporâneos, 10 famosos) com capas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--baixar-capas", action="store_true",
            help="Baixa as capas para media/capas/ (campo `capa`), p/ a feira funcionar offline. "
                 "O template prioriza o arquivo local sobre a URL.",
        )

    def handle(self, *args, **kwargs):
        criados = atualizados = 0
        for titulo, autor, area, desc, ano, estoque, cover_id in LIVROS:
            obj, created = Livro.objects.update_or_create(
                titulo=titulo,
                defaults={
                    "autor": autor,
                    "area": area,
                    "descricao": desc,
                    "ano": ano,
                    "estoque_total": estoque,
                    "capa_url": COV.format(cover_id),
                },
            )
            if created:
                criados += 1
            else:
                atualizados += 1

        for titulo, area, desc, titulos, destaque in COLECOES:
            col, _ = Colecao.objects.get_or_create(
                titulo=titulo,
                defaults={"area": area, "descricao": desc, "destaque": destaque},
            )
            for t in titulos:
                try:
                    col.livros.add(Livro.objects.get(titulo=t))
                except Livro.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  ! '{t}' não encontrado p/ lista '{titulo}'"))

        com_capa = Livro.objects.exclude(capa_url="").count()
        self.stdout.write(self.style.SUCCESS(
            f"Acervo pronto: {criados} criados, {atualizados} atualizados "
            f"({Livro.objects.count()} no total, {com_capa} com capa). "
            "Listas: Clássicos essenciais, Contemporâneos para começar, Famosos que todo mundo leu."
        ))

        if kwargs.get("baixar_capas"):
            self._baixar_capas()

    def _baixar_capas(self):
        """Baixa cada capa_url para o ImageField `capa` (modo feira offline).

        Os templates usam `livro.capa_src`, que prioriza o arquivo local.
        Capas inválidas (1x1 gif de 'não encontrado' ou HTTP != 200) são
        ignoradas — nesses casos o template mostra o placeholder retrô.
        """
        import urllib.request

        alvos = Livro.objects.exclude(capa_url="").filter(capa="")
        baixadas = ignoradas = 0
        for livro in alvos:
            try:
                req = urllib.request.Request(
                    livro.capa_url, headers={"User-Agent": "BiblioMatch-feira/1.0"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    if resp.status != 200:
                        raise ValueError(f"HTTP {resp.status}")
                    dados = resp.read()
                # Open Library devolve um gif 1x1 (~800 bytes) quando não há capa
                ctype = resp.headers.get_content_type()
                if len(dados) < 1500 and ctype in ("image/gif",):
                    raise ValueError("placeholder 1x1 (capa inexistente)")
                nome = f"seed_{livro.pk}.jpg"
                livro.capa.save(nome, ContentFile(dados), save=True)
                baixadas += 1
                self.stdout.write(f"  ok  {livro.titulo}")
            except Exception as exc:  # noqa: BLE001 — segue p/ o próximo livro
                ignoradas += 1
                self.stdout.write(self.style.WARNING(f"  ! {livro.titulo}: {exc}"))
        self.stdout.write(self.style.SUCCESS(
            f"Capas locais: {baixadas} baixadas, {ignoradas} ignoradas "
            "(ficam com placeholder retrô)."))
