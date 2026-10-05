# 📚 BiblioMatch — Sistema de Biblioteca Social

Projeto para **apresentação em feira**: Django + Tailwind (CDN), 100% responsivo, modo **claro/escuro** moderno.

## ✨ Funcionalidades (todas pedidas)

| Pedido | Onde está |
|---|---|
| Cadastro e gerenciamento de livros favoritos | Acervo → Favoritar / Meus favoritos / Cadastrar obra |
| Match literário (mesmo livro favoritado) | Automático ao favoritar → página de Matches |
| Notificações de match | Sino no topo + página Notificações |
| Lista de favoritos + ranking dos mais favoritados | Ranking com barras de progresso |
| Listas de recomendação por área/interesse | Listas da equipe (+ Nova lista) |
| Simulação de empréstimo | Solicitar com prazo (7/14/21 dias), renovar (até 2x), fila de reserva, multa simulada por atraso |
| Contato entre matches | Botão Contatar via WhatsApp na página de matches |
| Plataforma única, simples e social | Home + perfil + tudo integrado |

Sistema **não-rígido de propósito** (modo feira): senha simples liberada, qualquer logado cadastra livro/lista, desfavoritar não apaga histórico de match.

## 🚀 Rodar em 1 minuto (demo na feira)

```bash
# 1. Criar e ativar o ambiente virtual
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Instalar dependências e preparar o banco
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo   # cria 12 livros, 3 listas, usuários ana/123 bruno/123 carla/123 + matches
python manage.py runserver
```

Acesse `http://127.0.0.1:8000` 🎤

**Roteiro de apresentação (3 min):**
1. Crie uma conta (ou entre com `ana` / `123`)
2. No **Acervo**, favorite 2 obras → toast de **match literário**
3. Clique no sino → notificação de match
4. Abra **Matches** → veja a pessoa e a obra em comum, clique em **Contatar** (abre o WhatsApp)
5. Abra **Ranking** → mostre as barras de favoritos
6. Na página de uma obra, solicite um **empréstimo** com prazo de 7 dias → renove em **Empréstimos** → registre a **devolução**
7. Com o acervo zerado, mostre a **fila de reserva** e a notificação de disponibilidade
8. Alterne o tema claro/escuro e redimensione a tela (responsivo)

## 🛠 Stack

- Django 5 + SQLite (zero config)
- Tailwind via CDN, `darkMode: 'class'` + toggle com localStorage
- Sem build de front — ideal para apresentar offline/online

## 📁 Estrutura

```
config/        # settings, urls
core/          # models, views, urls, forms, templates, seed_demo
  templates/core/  # base + 12 páginas responsivas
```
