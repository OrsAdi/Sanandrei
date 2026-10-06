from django import forms

from .models import Order


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=20, initial=1)
    size = forms.CharField(required=False)

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        if product and product.size_list:
            self.fields["size"] = forms.ChoiceField(choices=[(s, s) for s in product.size_list], label="Mărime")


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["full_name", "phone", "email", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3})}
