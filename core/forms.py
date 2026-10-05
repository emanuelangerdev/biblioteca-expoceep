from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import AREAS, Colecao, Livro, Profile


class CadastroForm(UserCreationForm):
    telefone = forms.CharField(required=False, max_length=20,
                               widget=forms.TextInput(attrs={
                                   "class": "input",
                                   "placeholder": "11999998888 (só números, com DDD)"}))

    class Meta:
        model = User
        fields = ("username", "telefone", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "input")

    def save(self, commit=True):
        user = super().save(commit=commit)
        fone = (self.cleaned_data.get("telefone") or "").strip()
        if commit and fone:
            Profile.objects.update_or_create(
                usuario=user, defaults={"telefone": fone})
        elif not commit:
            # guarda p/ a view salvar junto (caso atípico)
            user._telefone_pendente = fone
        return user


class TelefoneForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["telefone"]
        widgets = {
            "telefone": forms.TextInput(attrs={
                "class": "input", "placeholder": "11999998888 (só números, com DDD)"}),
        }


class LivroForm(forms.ModelForm):
    class Meta:
        model = Livro
        fields = ["titulo", "autor", "area", "descricao", "ano", "isbn",
                  "capa_url", "capa", "estoque_total"]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "input", "placeholder": "Ex: Dom Casmurro"}),
            "autor": forms.TextInput(attrs={"class": "input", "placeholder": "Ex: Machado de Assis"}),
            "area": forms.Select(attrs={"class": "input"}),
            "descricao": forms.Textarea(attrs={"class": "input", "rows": 3,
                                               "placeholder": "Sinopse curta para a feira..."}),
            "ano": forms.NumberInput(attrs={"class": "input", "placeholder": "1899"}),
            "isbn": forms.TextInput(attrs={"class": "input", "placeholder": "978-..."}),
            "capa_url": forms.URLInput(attrs={"class": "input",
                                              "placeholder": "https://... (capa da internet)"}),
            "estoque_total": forms.NumberInput(attrs={"class": "input", "min": 1}),
        }


class ColecaoForm(forms.ModelForm):
    class Meta:
        model = Colecao
        fields = ["titulo", "descricao", "area", "livros", "destaque"]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "input"}),
            "descricao": forms.Textarea(attrs={"class": "input", "rows": 3}),
            "area": forms.Select(attrs={"class": "input"}),
            "livros": forms.SelectMultiple(attrs={"class": "input", "size": "8"}),
        }
