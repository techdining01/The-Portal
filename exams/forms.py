from django import forms
from .models import Quiz, Question, Choice, Subject, Class
from django.core.exceptions import ValidationError

class QuizCreateForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'subject', 'duration_minutes', 'is_published']

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'question_type', 'marks']

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ['text', 'is_correct']



class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name',]

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Create Class'}),
        }


class SubjectForm(forms.ModelForm):
    """
    Form for creating/editing subjects.
    """
    class Meta:
        model = Subject
        fields = ['code', 'name', 'description', 'category', 'level', 'credits', 'department', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'credits': forms.NumberInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if self.instance.pk:
            if Subject.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
                raise ValidationError(_('A subject with this code already exists.'))
        else:
            if Subject.objects.filter(code=code).exists():
                raise ValidationError(_('A subject with this code already exists.'))
        return code

